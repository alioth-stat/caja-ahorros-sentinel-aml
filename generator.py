"""Synthetic banking transaction stream -- stands in for a core banking
system's transaction log. 100% synthetic: Reto 5 provides no dataset and
forbids real customer data, so unlike Ovnicom's generator (which blends in
a real BIND9 capture) there's no real-data path here at all.

Amount distribution and channel mix are calibrated (not copied -- no raw
rows are redistributed) against the public Kaggle dataset "Bank Transaction
Dataset for Fraud Detection" (valakhorasani), 2,512 synthetic transactions:
TransactionAmount there has mean $297.59, std $291.95, right-skewed
(min $0.26, max $1,919.11) -- a lognormal shape, not uniform. Channel usage
splits roughly evenly across Branch/ATM/Online (868/833/811 of 2,512).

Maintains a small population of synthetic accounts, each with its own
baseline profile (typical amount scale, known payees, home branch/channel).
Most transactions are drawn straight from an account's own baseline
(benign). A small minority are one of 5 injected anomaly patterns -- see
detectors.py for what flags them.
"""
import random
import string
import time
from dataclasses import dataclass, field

BRANCHES = [
    "Panamá Centro", "Panamá Este", "Panamá Oeste", "Colón", "Coclé",
    "Veraguas", "Chiriquí", "Herrera", "Los Santos", "Bocas del Toro",
]
# sucursal=Branch, cajero=ATM, app+web split what the reference dataset
# calls "Online" into two digital sub-channels.
CHANNELS = ["app", "web", "sucursal", "cajero"]
_CHANNEL_WEIGHTS = [0.165, 0.165, 0.335, 0.335]
TX_TYPES = ["transferencia", "retiro", "deposito", "pago"]

_ACCOUNT_COUNT = 150
_STRUCTURING_THRESHOLD = 10_000.0  # ponytail: fixed demo threshold, not a real regulatory citation

# lognormal params fit to the reference dataset's mean/std via
# sigma^2 = ln(1 + (std/mean)^2), mu = ln(mean) - sigma^2/2
_AMOUNT_MU = 5.36
_AMOUNT_SIGMA = 0.55  # smaller than the dataset's 0.82: per-tx variability (see random_amount) covers the rest


@dataclass
class Transaction:
    ts: float
    account_id: str
    amount: float
    tx_type: str
    payee_id: str
    branch: str
    channel: str
    true_label: str = field(default="benign", repr=False)  # test/demo-accuracy only; pipeline never reads this


@dataclass
class _Account:
    account_id: str
    branch: str
    channel: str
    avg_amount: float
    known_payees: list

    def random_amount(self) -> float:
        return round(random.uniform(self.avg_amount * 0.3, self.avg_amount * 1.8), 2)

    def random_payee(self, new: bool = False) -> str:
        if new or not self.known_payees:
            payee = f"payee-{_random_id(6)}"
            self.known_payees.append(payee)
            if len(self.known_payees) > 12:
                self.known_payees.pop(0)
            return payee
        return random.choice(self.known_payees)


def _random_id(length: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _make_accounts(n: int) -> list:
    accounts = []
    for _ in range(n):
        branch = random.choice(BRANCHES)
        channel = random.choices(CHANNELS, weights=_CHANNEL_WEIGHTS)[0]
        avg_amount = min(max(random.lognormvariate(_AMOUNT_MU, _AMOUNT_SIGMA), 15), 1800)
        payees = [f"payee-{_random_id(6)}" for _ in range(random.randint(1, 5))]
        accounts.append(_Account(f"acc-{_random_id(8)}", branch, channel, avg_amount, payees))
    return accounts


_accounts = _make_accounts(_ACCOUNT_COUNT)


def _benign_tx(acc: _Account) -> Transaction:
    return Transaction(
        ts=time.time(),
        account_id=acc.account_id,
        amount=acc.random_amount(),
        tx_type=random.choice(TX_TYPES),
        payee_id=acc.random_payee(),
        branch=acc.branch,
        channel=acc.channel,
    )


def _structuring_burst(acc: _Account) -> list:
    # several transfers just under the reporting threshold, back to back
    n = random.randint(3, 5)
    return [
        Transaction(
            ts=time.time() + i * 0.01,
            account_id=acc.account_id,
            amount=round(_STRUCTURING_THRESHOLD - random.uniform(50, 500), 2),
            tx_type="transferencia",
            payee_id=acc.random_payee(),
            branch=acc.branch,
            channel=acc.channel,
            true_label="structuring",
        )
        for i in range(n)
    ]


def _velocity_burst(acc: _Account) -> list:
    # many small transactions in immediate succession, well above the
    # account's normal pace (pipeline sees these as one batch tick)
    n = random.randint(8, 14)
    return [
        Transaction(
            ts=time.time() + i * 0.01,
            account_id=acc.account_id,
            amount=acc.random_amount(),
            tx_type=random.choice(TX_TYPES),
            payee_id=acc.random_payee(),
            branch=acc.branch,
            channel=acc.channel,
            true_label="velocity_anomaly",
        )
        for i in range(n)
    ]


def _new_payee_large_tx(acc: _Account) -> Transaction:
    return Transaction(
        ts=time.time(),
        account_id=acc.account_id,
        amount=round(acc.avg_amount * random.uniform(6, 15), 2),
        tx_type="transferencia",
        payee_id=acc.random_payee(new=True),
        branch=acc.branch,
        channel=acc.channel,
        true_label="new_payee_risk",
    )


def _geo_channel_anomaly_tx(acc: _Account) -> Transaction:
    other_branch = random.choice([b for b in BRANCHES if b != acc.branch])
    other_channel = random.choice([c for c in CHANNELS if c != acc.channel])
    return Transaction(
        ts=time.time(),
        account_id=acc.account_id,
        amount=acc.random_amount(),
        tx_type=random.choice(TX_TYPES),
        payee_id=acc.random_payee(),
        branch=other_branch,
        channel=other_channel,
        true_label="geo_channel_anomaly",
    )


def _layering_burst(acc: _Account) -> list:
    # a large deposit followed immediately by transfers out to new payees
    deposit = Transaction(
        ts=time.time(),
        account_id=acc.account_id,
        amount=round(acc.avg_amount * random.uniform(8, 20), 2),
        tx_type="deposito",
        payee_id="n/a",
        branch=acc.branch,
        channel=acc.channel,
        true_label="layering",
    )
    outflows = [
        Transaction(
            ts=time.time() + 0.01 + i * 0.01,
            account_id=acc.account_id,
            amount=round(deposit.amount / random.uniform(2.5, 4), 2),
            tx_type="transferencia",
            payee_id=acc.random_payee(new=True),
            branch=acc.branch,
            channel=acc.channel,
            true_label="layering",
        )
        for i in range(random.randint(2, 3))
    ]
    return [deposit, *outflows]


_ANOMALY_GENERATORS = [
    _structuring_burst,
    _velocity_burst,
    lambda acc: [_new_payee_large_tx(acc)],
    lambda acc: [_geo_channel_anomaly_tx(acc)],
    _layering_burst,
]

# ponytail: fixed per-tick probability, not a target-rate controller -- tuned
# by hand so injected-anomaly volume lands near ~5% of total stream volume at
# pipeline.py's BATCH_SIZE/TICK_SECONDS (10 tx/sec baseline, ~4 tx/burst avg).
_ANOMALY_RATE = 0.15


def next_batch(size: int) -> list:
    batch = []
    for _ in range(size):
        acc = random.choice(_accounts)
        batch.append(_benign_tx(acc))
    if random.random() < _ANOMALY_RATE:
        acc = random.choice(_accounts)
        anomaly_fn = random.choice(_ANOMALY_GENERATORS)
        batch.extend(anomaly_fn(acc))
    return batch
