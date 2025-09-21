from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional
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


@router.get("/search")
async def search_events(
    stage: Optional[str] = None,
    ack_code: Optional[str] = None,
    hl7_type: Optional[str] = None,
    msg_id: Optional[str] = None,
    msh10: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    since: int = 86400,
    limit: int = 100,
    offset: int = 0,
):
    since = max(60, int(since or 0))
    limit = max(1, min(int(limit or 100), 500))
    offset = max(0, int(offset or 0))

    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
      SELECT id, ts, stage, msg_id, hl7_type, hl7_version, status, elapsed_ms, payload
      FROM events
      WHERE ts >= strftime('%s','now') - ?
      ORDER BY ts DESC
      LIMIT ? OFFSET ?
    """,
        (since, limit, offset),
    )
    rows = cur.fetchall()

    def match(row: tuple) -> bool:
        _id, ts, stg, mid, t, ver, st, elapsed, payload = row
        if stage and stg != stage:
            return False
        if status and st != status:
            return False
        if hl7_type and t != hl7_type:
            return False
        if msg_id and mid != msg_id:
            return False
        try:
            parsed = json.loads(payload or "{}")
        except Exception:
            parsed = {}
        if ack_code and str(parsed.get("ack_code", "")).upper() != ack_code.upper():
            return False
        if msh10 and str(parsed.get("msh10", "")) != msh10:
            return False
        if q:
            body = (payload or "").lower()
            if q.lower() not in body:
                return False
        return True

    items = []
    for row in rows:
        if not match(row):
            continue
        _id, ts, stg, mid, t, ver, st, elapsed, payload = row
        items.append(
            {
                "id": _id,
                "ts": ts,
                "stage": stg,
                "msg_id": mid,
                "hl7_type": t,
                "hl7_version": ver,
                "status": st,
                "elapsed_ms": elapsed,
                "payload": payload,
            }
        )

    return JSONResponse({"count": len(items), "items": items})

@router.get("/validate_summary")
async def validate_summary(window: int = 86400):
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
      SELECT COUNT(*) as total,
             SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as ok,
             AVG(elapsed_ms) as avg_ms
      FROM events
      WHERE stage='validate' AND ts >= strftime('%s','now') - ?
    """,
        (window,),
    )
    row = cur.fetchone() or (0, 0, 0)
    total, ok, avg_ms = row

    cur.execute(
        """
      SELECT payload FROM events
      WHERE stage='validate' AND ts >= strftime('%s','now') - ?
    """,
        (window,),
    )
    import collections

    counter = collections.Counter()
    for (payload,) in cur.fetchall():
        try:
            parsed = json.loads(payload or "{}")
        except Exception:
            parsed = {}
        top = parsed.get("top_errors") or []
        if isinstance(top, dict):
            counter.update(top.keys())
        elif isinstance(top, list):
            counter.update(str(item) for item in top)

    top_errors = [{"code": code, "count": count} for code, count in counter.most_common(10)]
    return JSONResponse(
        {
            "total": total or 0,
            "successes": ok or 0,
            "success_rate": (ok or 0) / max(total or 1, 1),
            "avg_ms": int(avg_ms or 0),
            "top_errors": top_errors,
        }
    )


@router.get("/validate_search")
async def validate_search(q: str = "", window: int = 86400, limit: int = 100):
    window = max(60, int(window or 0))
    limit = max(1, min(int(limit or 100), 500))
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
      SELECT id, ts, stage, msg_id, hl7_type, hl7_version, status, elapsed_ms, payload
      FROM events
      WHERE stage='validate' AND ts >= strftime('%s','now') - ?
      ORDER BY ts DESC LIMIT ?
    """,
        (window, limit),
    )
    rows = cur.fetchall()
    items = []
    for row in rows:
        _id, ts, stg, mid, hl7_type, hl7_version, status, elapsed_ms, payload = row
        try:
            parsed = json.loads(payload or "{}")
        except Exception:
            parsed = {}
        search_blob = json.dumps(parsed, separators=(",", ":")).lower()
        if q and q.lower() not in search_blob:
            continue
        items.append(
            {
                "id": _id,
                "ts": ts,
                "msg_id": mid,
                "hl7_type": hl7_type,
                "hl7_version": hl7_version,
                "status": status,
                "elapsed_ms": elapsed_ms,
                "payload": parsed,
            }
        )
    return JSONResponse({"count": len(items), "items": items})
