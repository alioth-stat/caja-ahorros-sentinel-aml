"""Two decoupled background tasks, not one: ingestion runs at the stream's
real rate (10 tx/sec target), but QVAC can only judge roughly one candidate
every 15-25s on this hardware (a single shared event loop + lock in
qvac_client.py serializes every call -- see its ponytail: comments). Feeding
candidates into the judge inline, like Ovnicom Sentinel-DNS's pipeline.py
does, would stall transaction ingestion itself behind QVAC's much slower
pace. So: `ingest_forever` reads the stream, runs the free heuristics, and
either fast-rejects (frozen account) or drops flagged candidates onto a
queue; `judge_forever` drains that queue at whatever pace QVAC can sustain.
The queue backlog (`pending_review` in stats) is the honest, visible cost of
that pace difference -- not hidden.

Tiering policy: a non-benign verdict at or above 85% confidence is treated
as high-confidence enough to act on automatically (freeze the account,
surface it in red) rather than just queued for a human analyst -- this
mirrors how a real bank's fraud system would only auto-act past a high
confidence bar, and route the ambiguous middle to manual review.
"""
import asyncio
import itertools
import time
from collections import deque

import compliance_sink
import db
import detectors
import generator
import qvac_judge

TICK_SECONDS = 1.0
BATCH_SIZE = 10  # ~10 tx/sec baseline -- the demo-scale stand-in for Caja de Ahorros' real ~600 tx/sec

CRITICAL_CONFIDENCE = 0.85

_FEED_MAX = 300
_feed: dict[int, dict] = {}
_next_tx_id = itertools.count(1)
_tx_timestamps: deque = deque(maxlen=1000)  # for the rolling tx/sec stat


def _record_feed(tx_id: int, tx, status: str, **extra) -> None:
    _feed[tx_id] = {
        "id": tx_id, "ts": tx.ts, "account_id": tx.account_id, "amount": tx.amount,
        "tx_type": tx.tx_type, "branch": tx.branch, "channel": tx.channel, "status": status, **extra,
    }
    while len(_feed) > _FEED_MAX:
        _feed.pop(next(iter(_feed)))


def get_feed(limit: int = 50) -> list[dict]:
    return list(_feed.values())[-limit:][::-1]


def get_throughput() -> dict:
    now = time.time()
    recent = [t for t in _tx_timestamps if now - t <= 5]
    return {"tx_per_second": round(len(recent) / 5, 1), "pending_review": _queue.qsize() if _queue else 0}


_queue: asyncio.Queue | None = None


async def ingest_forever(conn) -> None:
    global _queue
    _queue = asyncio.Queue()
    while True:
        for tx in generator.next_batch(BATCH_SIZE):
            tx_id = next(_next_tx_id)
            _tx_timestamps.append(tx.ts)

            if db.is_frozen(conn, tx.account_id):
                _record_feed(tx_id, tx, "frozen_blocked")
                continue

            candidate = detectors.classify_candidate(tx)
            if candidate is None:
                _record_feed(tx_id, tx, "normal")
            else:
                _record_feed(tx_id, tx, "pending", heuristic_kind=candidate["kind"])
                await _queue.put((tx_id, tx, candidate))

        await asyncio.sleep(TICK_SECONDS)


async def judge_forever(conn) -> None:
    loop = asyncio.get_running_loop()
    queue = _queue
    while queue is None:  # ingest_forever hasn't created it yet
        await asyncio.sleep(0.05)
        queue = _queue

    while True:
        tx_id, tx, candidate = await queue.get()
        verdict = await loop.run_in_executor(None, qvac_judge.classify, tx, candidate)

        entry = _feed.get(tx_id)
        if verdict["verdict"] == "benign":
            if entry is not None:
                entry["status"] = "benign"
                entry["confidence"] = verdict["confidence"]
            continue

        tier = "critical" if verdict["confidence"] >= CRITICAL_CONFIDENCE else "review"
        alert_id = db.insert_alert(conn, tx, candidate, verdict, tier)
        compliance_sink.append_alert(tx, candidate, verdict)
        if tier == "critical":
            db.freeze_account(conn, tx.account_id, verdict["verdict"], verdict["confidence"], alert_id)

        if entry is not None:
            entry["status"] = verdict["verdict"]
            entry["tier"] = tier
            entry["confidence"] = verdict["confidence"]
            entry["reasoning"] = verdict["reasoning"]


async def run_forever(conn) -> None:
    await asyncio.gather(ingest_forever(conn), judge_forever(conn))
