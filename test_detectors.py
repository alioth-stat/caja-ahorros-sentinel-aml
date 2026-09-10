import detectors
from generator import Transaction


def _tx(account_id, ts, amount, tx_type="transferencia", payee_id="payee-1", branch="Panamá Centro", channel="app"):
    return Transaction(ts=ts, account_id=account_id, amount=amount, tx_type=tx_type, payee_id=payee_id, branch=branch, channel=channel)


def test_structuring_flags_repeated_near_threshold_transfers():
    acc = "acc-structuring-test"
    for i in range(2):
        assert detectors.classify_candidate(_tx(acc, 1000.0 + i, 9800.0, payee_id=f"payee-{i}")) is None
    result = detectors.classify_candidate(_tx(acc, 1002.0, 9700.0, payee_id="payee-2"))
    assert result is not None
    assert result["kind"] == "structuring"


def test_structuring_ignores_normal_amounts():
    acc = "acc-structuring-normal"
    for i in range(5):
        assert detectors.classify_candidate(_tx(acc, 2000.0 + i, 300.0)) is None


def test_velocity_flags_burst_of_transactions():
    acc = "acc-velocity-test"
    result = None
    for i in range(8):
        result = detectors.classify_candidate(_tx(acc, 3000.0 + i * 0.1, 100.0, payee_id=f"payee-{i}"))
    assert result is not None
    assert result["kind"] == "velocity_anomaly"


def test_velocity_ignores_spaced_out_transactions():
    acc = "acc-velocity-normal"
    result = None
    for i in range(8):
        result = detectors.classify_candidate(_tx(acc, 4000.0 + i * 20.0, 100.0))
    assert result is None


def test_new_payee_large_flags_unfamiliar_big_transfer():
    acc = "acc-new-payee-test"
    for i in range(4):
        assert detectors.classify_candidate(_tx(acc, 5000.0 + i, 100.0, payee_id="payee-regular")) is None
    result = detectors.classify_candidate(_tx(acc, 5010.0, 900.0, payee_id="payee-stranger"))
    assert result is not None
    assert result["kind"] == "new_payee_risk"


def test_new_payee_ignores_known_payee_large_transfer():
    acc = "acc-known-payee-test"
    for i in range(4):
        assert detectors.classify_candidate(_tx(acc, 6000.0 + i, 100.0, payee_id="payee-regular")) is None
    result = detectors.classify_candidate(_tx(acc, 6010.0, 900.0, payee_id="payee-regular"))
    assert result is None


def test_geo_channel_anomaly_flags_unusual_branch_and_channel():
    acc = "acc-geo-test"
    for i in range(4):
        assert detectors.classify_candidate(_tx(acc, 7000.0 + i, 100.0, branch="Chiriquí", channel="app")) is None
    result = detectors.classify_candidate(_tx(acc, 7010.0, 100.0, branch="Colón", channel="cajero"))
    assert result is not None
    assert result["kind"] == "geo_channel_anomaly"


def test_layering_flags_new_payee_transfer_shortly_after_large_deposit():
    acc = "acc-layering-test"
    for i in range(4):
        assert detectors.classify_candidate(_tx(acc, 8000.0 + i, 100.0, tx_type="pago", payee_id="n/a")) is None
    deposit_result = detectors.classify_candidate(_tx(acc, 8010.0, 5000.0, tx_type="deposito", payee_id="n/a"))
    assert deposit_result is None  # the deposit itself isn't the flagged event
    result = detectors.classify_candidate(_tx(acc, 8011.0, 1500.0, tx_type="transferencia", payee_id="payee-stranger"))
    assert result is not None
    assert result["kind"] == "layering"


def test_layering_window_expires():
    acc = "acc-layering-expired-test"
    for i in range(4):
        assert detectors.classify_candidate(_tx(acc, 9000.0 + i, 100.0, tx_type="pago", payee_id="n/a")) is None
    assert detectors.classify_candidate(_tx(acc, 9010.0, 5000.0, tx_type="deposito", payee_id="n/a")) is None
    late_transfer = _tx(acc, 9010.0 + detectors._LAYERING_WINDOW_S + 5, 1500.0, tx_type="transferencia", payee_id="payee-stranger")
    result = detectors.classify_candidate(late_transfer)
    assert result is None or result["kind"] != "layering"
