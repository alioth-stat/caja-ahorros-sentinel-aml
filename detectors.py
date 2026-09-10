"""Cheap rule-based heuristics that flag transaction candidates worth a QVAC
opinion. Runs on every transaction inline (no model, no I/O) -- the point is
to filter a firehose down to the handful of candidates actually worth an LLM
call. Same shape as Ovnicom Sentinel-DNS's detectors.py, different domain.

Each account's baseline (typical amount, known payees, usual branch/channel)
is learned from what this module has observed in the stream so far -- it
never reads the generator's internal ground truth, same as a real detector
would only ever see the transaction stream itself.
"""
from collections import defaultdict, deque

_HISTORY_LEN = 30
_MIN_HISTORY_FOR_BASELINE = 3

_STRUCTURING_THRESHOLD = 10_000.0  # must match generator.py's demo threshold
_STRUCTURING_MARGIN = 500.0  # "just under" band width
_STRUCTURING_WINDOW_S = 60
_STRUCTURING_MIN_HITS = 3

_VELOCITY_WINDOW_S = 10
_VELOCITY_MIN_HITS = 6

_NEW_PAYEE_AMOUNT_FACTOR = 4.0

_LAYERING_DEPOSIT_FACTOR = 5.0
_LAYERING_WINDOW_S = 30

# ponytail: per-process in-memory history, capped by simple eviction -- a
# real deployment would key this off the core banking event stream's own
# windowing instead of reinventing one, but a hackathon single-process demo
# doesn't have that.
_account_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=_HISTORY_LEN))
_recent_timestamps: dict[str, list] = defaultdict(list)
_pending_deposit: dict[str, tuple] = {}
_MAX_TRACKED_ACCOUNTS = 5000


def _baseline_amount(history: deque) -> float:
    amounts = [t.amount for t in history]
    return sum(amounts) / len(amounts) if amounts else 0.0


def _known_payees(history: deque) -> set:
    return {t.payee_id for t in history}


def _mode_branch_channel(history: deque) -> tuple[str | None, str | None]:
    branches = [t.branch for t in history]
    channels = [t.channel for t in history]
    mode_branch = max(set(branches), key=branches.count) if branches else None
    mode_channel = max(set(channels), key=channels.count) if channels else None
    return mode_branch, mode_channel


def score_structuring(tx, history: deque) -> float:
    if tx.tx_type != "transferencia":
        return 0.0
    if not (_STRUCTURING_THRESHOLD - _STRUCTURING_MARGIN <= tx.amount < _STRUCTURING_THRESHOLD):
        return 0.0
    recent = [
        t for t in history
        if tx.ts - t.ts <= _STRUCTURING_WINDOW_S
        and _STRUCTURING_THRESHOLD - _STRUCTURING_MARGIN <= t.amount < _STRUCTURING_THRESHOLD
    ]
    hits = len(recent) + 1  # +1 for tx itself
    if hits < _STRUCTURING_MIN_HITS:
        return 0.0
    return min(0.5 + 0.15 * (hits - _STRUCTURING_MIN_HITS), 1.0)


def score_velocity(tx, account_id: str) -> float:
    timestamps = _recent_timestamps[account_id]
    timestamps.append(tx.ts)
    timestamps[:] = [t for t in timestamps if tx.ts - t <= _VELOCITY_WINDOW_S]
    if len(_recent_timestamps) > _MAX_TRACKED_ACCOUNTS:
        _recent_timestamps.clear()  # ponytail: drop everything rather than LRU-evict; demo-scale only
    hits = len(timestamps)
    if hits < _VELOCITY_MIN_HITS:
        return 0.0
    return min(0.5 + 0.05 * (hits - _VELOCITY_MIN_HITS), 1.0)


def score_new_payee_large(tx, history: deque) -> float:
    if len(history) < _MIN_HISTORY_FOR_BASELINE or tx.payee_id in _known_payees(history):
        return 0.0
    baseline = _baseline_amount(history)
    if baseline <= 0 or tx.amount < baseline * _NEW_PAYEE_AMOUNT_FACTOR:
        return 0.0
    ratio = tx.amount / baseline
    return min(0.4 + 0.1 * (ratio - _NEW_PAYEE_AMOUNT_FACTOR), 1.0)


def score_geo_channel_anomaly(tx, history: deque) -> float:
    if len(history) < _MIN_HISTORY_FOR_BASELINE:
        return 0.0
    mode_branch, mode_channel = _mode_branch_channel(history)
    score = 0.0
    if tx.branch != mode_branch:
        score += 0.5
    if tx.channel != mode_channel:
        score += 0.3
    return min(score, 1.0)


def score_layering(tx, account_id: str, history: deque) -> tuple[float, float | None]:
    if tx.tx_type == "deposito":
        baseline = _baseline_amount(history)
        if len(history) >= _MIN_HISTORY_FOR_BASELINE and baseline > 0 and tx.amount >= baseline * _LAYERING_DEPOSIT_FACTOR:
            _pending_deposit[account_id] = (tx.ts, tx.amount)
        return 0.0, None  # the deposit itself isn't the flagged event, the outflow after it is

    pending = _pending_deposit.get(account_id)
    if not pending:
        return 0.0, None
    deposit_ts, deposit_amount = pending
    if tx.ts - deposit_ts > _LAYERING_WINDOW_S:
        del _pending_deposit[account_id]
        return 0.0, None
    if tx.tx_type == "transferencia" and tx.payee_id not in _known_payees(history):
        del _pending_deposit[account_id]  # one flagged outflow consumes the pending deposit
        return 0.8, deposit_amount
    return 0.0, None


_CANDIDATE_THRESHOLD = 0.5


def classify_candidate(tx) -> dict | None:
    """Return heuristic signals if tx is worth escalating to QVAC, else None."""
    history = _account_history[tx.account_id]

    layering_score, layering_deposit = score_layering(tx, tx.account_id, history)
    signals = {
        "structuring": score_structuring(tx, history),
        "velocity_anomaly": score_velocity(tx, tx.account_id),
        "new_payee_risk": score_new_payee_large(tx, history),
        "geo_channel_anomaly": score_geo_channel_anomaly(tx, history),
        "layering": layering_score,
    }

    history.append(tx)  # update baseline AFTER scoring, so tx doesn't inflate its own baseline
    if len(_account_history) > _MAX_TRACKED_ACCOUNTS:
        _account_history.clear()

    top_kind = max(signals, key=signals.get)
    top_score = signals[top_kind]
    if top_score < _CANDIDATE_THRESHOLD:
        return None

    return {
        "kind": top_kind,
        "heuristic_score": round(top_score, 2),
        "layering_deposit_amount": round(layering_deposit, 2) if top_kind == "layering" and layering_deposit else None,
        "signals": {k: round(v, 2) for k, v in signals.items()},
    }
