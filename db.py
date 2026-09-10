"""SQLite storage for alerts and frozen accounts. Plain functions over
sqlite3.Connection, no ORM -- stands in for a bank's core banking /
case-management database. Same shape as Ovnicom Sentinel-DNS's db.py, minus
its second (QoE) table -- Reto 5 doesn't require a dual output."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def init_db(path: str = "sentinel_aml.db") -> sqlite3.Connection:
    is_new = not Path(path).exists()
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            amount REAL,
            tx_type TEXT,
            payee_id TEXT,
            branch TEXT,
            channel TEXT,
            heuristic_kind TEXT,
            heuristic_score REAL,
            verdict TEXT,
            confidence REAL,
            reasoning TEXT,
            tier TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS frozen_accounts (
            account_id TEXT PRIMARY KEY,
            reason TEXT,
            confidence REAL,
            alert_id INTEGER,
            frozen_at TEXT
        )
    """)
    conn.commit()
    _ = is_new  # nothing to seed for this domain
    return conn


def insert_alert(conn: sqlite3.Connection, tx, candidate: dict, verdict: dict, tier: str) -> int:
    cur = conn.execute(
        """INSERT INTO alerts
           (account_id, amount, tx_type, payee_id, branch, channel,
            heuristic_kind, heuristic_score, verdict, confidence, reasoning, tier, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            tx.account_id, tx.amount, tx.tx_type, tx.payee_id, tx.branch, tx.channel,
            candidate["kind"], candidate["heuristic_score"],
            verdict["verdict"], verdict["confidence"], verdict["reasoning"], tier,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_recent_alerts(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS n FROM alerts").fetchone()["n"]
    by_kind = conn.execute(
        "SELECT verdict, COUNT(*) AS n FROM alerts WHERE verdict != 'benign' GROUP BY verdict"
    ).fetchall()
    by_tier = conn.execute(
        "SELECT tier, COUNT(*) AS n FROM alerts WHERE verdict != 'benign' GROUP BY tier"
    ).fetchall()
    frozen = conn.execute("SELECT COUNT(*) AS n FROM frozen_accounts").fetchone()["n"]
    return {
        "total_alerts": total,
        "by_kind": {r["verdict"]: r["n"] for r in by_kind},
        "by_tier": {r["tier"]: r["n"] for r in by_tier},
        "frozen_accounts": frozen,
    }


def freeze_account(conn: sqlite3.Connection, account_id: str, reason: str, confidence: float, alert_id: int) -> None:
    conn.execute(
        """INSERT INTO frozen_accounts (account_id, reason, confidence, alert_id, frozen_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(account_id) DO NOTHING""",
        (account_id, reason, confidence, alert_id, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def is_frozen(conn: sqlite3.Connection, account_id: str) -> bool:
    return conn.execute("SELECT 1 FROM frozen_accounts WHERE account_id = ?", (account_id,)).fetchone() is not None


def get_frozen_accounts(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute("SELECT * FROM frozen_accounts ORDER BY frozen_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
