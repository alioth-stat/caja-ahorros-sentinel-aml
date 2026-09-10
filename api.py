"""FastAPI wrapper -- no business logic lives here, same pattern as the
Philips/Ovnicom submissions' api.py. Routes are plain `def` (read-only
queries against state the background pipeline maintains); the pipeline
itself is started from the lifespan hook, not a route, since it must run
continuously.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import compliance_sink
import db
import pipeline

_VALID_ACTIONS = {"freeze", "skip", "contact", "escalate"}


class AlertAction(BaseModel):
    action: str

conn = db.init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(pipeline.run_forever(conn))
    yield
    task.cancel()


app = FastAPI(title="Caja de Ahorros Sentinel-AML API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/alerts")
def list_alerts(limit: int = 50):
    return db.get_recent_alerts(conn, limit)


@app.get("/api/feed")
def feed(limit: int = 50):
    return pipeline.get_feed(limit)


@app.get("/api/frozen")
def frozen(limit: int = 50):
    return db.get_frozen_accounts(conn, limit)


@app.get("/api/stats")
def stats():
    return {**db.get_stats(conn), **pipeline.get_throughput()}


@app.post("/api/alerts/{alert_id}/action")
def act_on_alert(alert_id: int, body: AlertAction):
    if body.action not in _VALID_ACTIONS:
        raise HTTPException(400, f"invalid action: {body.action!r}, must be one of {sorted(_VALID_ACTIONS)}")
    alert = db.get_alert(conn, alert_id)
    if alert is None:
        raise HTTPException(404, "alert not found")

    if body.action == "freeze":
        db.freeze_account(conn, alert["account_id"], alert["verdict"], alert["confidence"], alert_id)
    db.set_alert_action(conn, alert_id, body.action)
    compliance_sink.append_action(alert, body.action)
    return db.get_alert(conn, alert_id)
