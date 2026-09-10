"""Appends confirmed alerts as JSON lines to a local case log, in the shape a
bank's AML/fraud case-management queue could ingest -- same integration
pattern as Ovnicom Sentinel-DNS's wazuh_sink.py (tail a JSON log), reframed
as a compliance case export instead of a SIEM rule, since a bank's fraud/AML
team works case queues, not a security SIEM."""
import json
from datetime import datetime, timezone
from pathlib import Path

_LOG_PATH = Path("compliance_case_log.log")

_SEVERITY_BY_KIND = {
    "structuring": 9, "layering": 9, "new_payee_risk": 7,
    "velocity_anomaly": 6, "geo_channel_anomaly": 6,
}


def append_alert(tx, candidate: dict, verdict: dict) -> None:
    kind = verdict["verdict"]
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case": {
            "severity": _SEVERITY_BY_KIND.get(kind, 5),
            "description": f"Sentinel-AML: {kind} sospechoso detectado por QVAC",
            "tags": ["aml", "sentinel-aml", kind],
        },
        "data": {
            "transaction": {
                "account_id": tx.account_id,
                "amount": tx.amount,
                "tx_type": tx.tx_type,
                "payee_id": tx.payee_id,
                "branch": tx.branch,
                "channel": tx.channel,
                "heuristic_kind": candidate["kind"],
                "heuristic_score": candidate["heuristic_score"],
                "verdict": kind,
                "confidence": verdict["confidence"],
                "reasoning": verdict["reasoning"],
            },
        },
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_action(alert: dict, action: str) -> None:
    """An analyst acted on an already-confirmed alert from the detail view
    (freeze/skip/contact/escalate) -- logged the same way as the original
    alert so a real case system sees the full lifecycle, not just the open."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case": {
            "description": f"Sentinel-AML: analyst action '{action}' on alert #{alert['id']}",
            "tags": ["aml", "sentinel-aml", "analyst-action", action],
        },
        "data": {"alert_id": alert["id"], "account_id": alert["account_id"], "action": action},
    }
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
