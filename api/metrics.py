from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict
import hashlib
import hmac

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

DB_PATH = Path(os.getenv("SILHOUETTE_DB", "silhouette_metrics.db"))
SECRET = os.getenv("SILHOUETTE_HMAC", "change-me")

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      stage TEXT NOT NULL,
      msg_id TEXT,
      hl7_type TEXT,
      hl7_version TEXT,
      status TEXT,
      elapsed_ms INTEGER,
      payload TEXT
    )
    """
    )
    return con


def _pseudonymize(value: str) -> str:
    if not value:
        return ""
    return hmac.new(SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()[:16]


def record_event(data: Dict[str, Any]) -> None:
    clean = dict(data)
    for key in ("patient_name", "mrn", "dob", "address", "phone"):
        if key in clean and clean[key] is not None:
            clean[key] = _pseudonymize(str(clean[key]))
    stage = clean.get("stage", "unknown")
    msg_id = clean.get("msg_id")
    hl7_type = clean.get("hl7_type")
    hl7_version = clean.get("hl7_version")
    status = clean.get("status", "success")
    try:
        elapsed_ms = int(clean.get("elapsed_ms") or 0)
    except (TypeError, ValueError):
        elapsed_ms = 0
    payload = json.dumps(clean, separators=(",", ":"))
    con = _conn()
    with con:
        con.execute(
            "INSERT INTO events (ts, stage, msg_id, hl7_type, hl7_version, status, elapsed_ms, payload) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                int(time.time()),
                stage,
                msg_id,
                hl7_type,
                hl7_version,
                status,
                elapsed_ms,
                payload,
            ),
        )


@router.post("/event")
async def post_event(req: Request):
    data: Dict[str, Any] = await req.json()
    record_event(data)
    return JSONResponse({"ok": True})


@router.get("/summary")
async def get_summary(window: int = 86400):
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
        AVG(elapsed_ms) as avg_ms
      FROM events
      WHERE ts >= strftime('%s','now') - ?
    """,
        (window,),
    )
    total, successes, avg_ms = cur.fetchone()
    cur.execute(
        """
      SELECT stage, COUNT(*) cnt FROM events
      WHERE ts >= strftime('%s','now') - ?
      GROUP BY stage ORDER BY cnt DESC
    """,
        (window,),
    )
    by_stage = [{"stage": s, "count": c} for s, c in cur.fetchall()]
    cur.execute(
        """
      SELECT status, COUNT(*) cnt FROM events
      WHERE ts >= strftime('%s','now') - ?
      GROUP BY status
    """,
        (window,),
    )
    by_status = [{"status": s, "count": c} for s, c in cur.fetchall()]
    cur.execute(
        """
      SELECT hl7_type, COUNT(*) cnt FROM events
      WHERE ts >= strftime('%s','now') - ?
      GROUP BY hl7_type ORDER BY cnt DESC LIMIT 10
    """,
        (window,),
    )
    top_types = [{"hl7_type": t, "count": c} for t, c in cur.fetchall()]
    return JSONResponse(
        {
            "window": window,
            "total": total or 0,
            "successes": successes or 0,
            "success_rate": (successes or 0) / (total or 1),
            "avg_ms": int(avg_ms or 0),
            "by_stage": by_stage,
            "by_status": by_status,
            "top_types": top_types,
        }
    )
