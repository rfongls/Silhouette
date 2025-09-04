from __future__ import annotations

import json, os
from pathlib import Path

from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse

router = APIRouter()


def _backup(path: Path) -> None:
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def _ensure_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


@router.post("/admin/seeds/save")
async def save_seeds(
    cve_json: str = Form(...),
    kev_json: str = Form(...),
    scope_text: str = Form(...),
):
    try:
        json.loads(cve_json)
        json.loads(kev_json)
    except json.JSONDecodeError as e:
        data = {"ok": False, "error": str(e)}
        return PlainTextResponse(json.dumps(data), status_code=400, media_type="application/json")

    cve_path = Path("data/security/seeds/cve/cve_seed.json")
    kev_path = Path("data/security/seeds/kev/kev_seed.json")
    scope_path = Path("docs/cyber/scope_example.txt")

    _ensure_parent(cve_path)
    _ensure_parent(kev_path)
    _ensure_parent(scope_path)

    _backup(cve_path)
    cve_path.write_text(cve_json, encoding="utf-8")
    _backup(kev_path)
    kev_path.write_text(kev_json, encoding="utf-8")
    _backup(scope_path)
    scope_path.write_text(scope_text, encoding="utf-8")

    return PlainTextResponse(json.dumps({"ok": True}), media_type="application/json")


@router.post("/admin/safety/save")
async def save_safety(
    CYBER_KILL_SWITCH: str = Form("false"),
    CYBER_DENY_LIST: str = Form(""),
    CYBER_PENTEST_WINDOW: str = Form(""),
    CYBER_THROTTLE_SECONDS: str = Form(""),
    CYBER_ALLOWLIST: str = Form(""),
    CYBER_DNS_DIR: str = Form(""),
    CYBER_HTTP_DIR: str = Form(""),
):
    path = Path("config/security.env")
    _ensure_parent(path)
    _backup(path)
    lines = [
        f"CYBER_KILL_SWITCH={CYBER_KILL_SWITCH}",
        f"CYBER_DENY_LIST={CYBER_DENY_LIST}",
        f"CYBER_PENTEST_WINDOW={CYBER_PENTEST_WINDOW}",
        f"CYBER_THROTTLE_SECONDS={CYBER_THROTTLE_SECONDS}",
        f"CYBER_ALLOWLIST={CYBER_ALLOWLIST}",
        f"CYBER_DNS_DIR={CYBER_DNS_DIR}",
        f"CYBER_HTTP_DIR={CYBER_HTTP_DIR}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return PlainTextResponse(json.dumps({"ok": True}), media_type="application/json")
