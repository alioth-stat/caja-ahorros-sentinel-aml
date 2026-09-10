"""QVAC structured classification of a heuristic-flagged transaction. Same
shape as Ovnicom Sentinel-DNS's qvac_judge.py (itself patterned on Philips'
extract.py): JSON-schema-constrained decoding + a short retry loop."""
import json

import qvac_client

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [
                "benign", "structuring", "velocity_anomaly", "new_payee_risk",
                "geo_channel_anomaly", "layering",
            ],
        },
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["verdict", "confidence", "reasoning"],
}

SYSTEM_PROMPT = """Eres un analista de prevención de fraude y lavado de dinero (AML) de un banco. \
Un sistema heurístico ya revisó una transacción y determinó su tipo de sospecha más probable, de \
esta lista: structuring (estructuración para evadir un umbral de reporte), velocity_anomaly \
(velocidad anómala de transacciones), new_payee_risk (transferencia grande a un beneficiario \
nuevo), geo_channel_anomaly (anomalía de sucursal o canal), o layering (movimiento rápido de \
fondos tras un depósito grande).

Tu trabajo NO es adivinar el tipo desde cero: la mayoría de las veces, el tipo que ya te indica el \
heurístico es correcto y solo debes confirmarlo. Cámbialo a otro tipo de la lista únicamente si el \
contexto de la transacción lo contradice claramente, o descártalo como "benign" si no ves ninguna \
razón real de sospecha.

Responde ÚNICAMENTE con el objeto JSON: verdict (uno de benign, structuring, velocity_anomaly, \
new_payee_risk, geo_channel_anomaly, layering), confidence (0 a 1), reasoning (una frase breve en \
español explicando por qué, para un analista de cumplimiento sin contexto de ML).
"""

_FALLBACK = {"verdict": "benign", "confidence": 0.0, "reasoning": "No se pudo obtener un veredicto del modelo."}

_KIND_LABELS = {
    "structuring": "estructuración (transferencias justo debajo de un umbral de reporte)",
    "velocity_anomaly": "velocidad anómala de transacciones",
    "new_payee_risk": "transferencia grande a un beneficiario nuevo",
    "geo_channel_anomaly": "anomalía de sucursal o canal",
    "layering": "layering (movimiento rápido de fondos tras un depósito grande)",
}


def _format_candidate(tx, candidate: dict) -> str:
    kind = candidate["kind"]
    text = (
        f"Cuenta: {tx.account_id}\n"
        f"Monto: {tx.amount}\n"
        f"Tipo: {tx.tx_type}\n"
        f"Beneficiario: {tx.payee_id}\n"
        f"Sucursal/canal: {tx.branch} / {tx.channel}\n"
        f"Tipo de sospecha determinado por el heurístico: {kind} ({_KIND_LABELS.get(kind, kind)}), "
        f"con score {candidate['heuristic_score']} sobre 1.\n"
    )
    if candidate.get("layering_deposit_amount"):
        text += f"Depósito grande previo en la misma cuenta: {candidate['layering_deposit_amount']}\n"
    return text


def classify(tx, candidate: dict) -> dict:
    text = _format_candidate(tx, candidate)
    # ponytail: same cold-load flakiness as Philips' extract.py -- retry once
    # on malformed JSON before falling back to a safe "benign, low confidence".
    for attempt in range(2):
        raw_text = qvac_client.extract_sync(text, JSON_SCHEMA, system_prompt=SYSTEM_PROMPT)
        try:
            raw = json.loads(raw_text)
            if raw and raw.get("verdict") and raw.get("reasoning"):
                raw["confidence"] = float(raw.get("confidence") or 0.0)
                return raw
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        print(f"qvac_judge: attempt {attempt + 1} did not return a usable verdict, got: {raw_text!r}")
    return dict(_FALLBACK)
