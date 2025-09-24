from __future__ import annotations
import json, subprocess, time, shutil, re, io, csv, datetime, textwrap, tempfile, uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
import threading
from urllib.parse import parse_qs
from fastapi import APIRouter, UploadFile, File, Form, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from starlette.templating import Jinja2Templates
from api.ui import install_link_for
try:
    import requests  # for optional FHIR reads
except Exception:  # pragma: no cover - optional dependency
    requests = None

from skills.hl7_drafter import draft_message, send_message
from silhouette_core.interop.hl7_mutate import (
    enrich_clinical_fields,
    ensure_unique_fields,
)
from silhouette_core.interop.deid import deidentify_message, apply_deid_with_template
from silhouette_core.interop.validate_workbook import validate_message, validate_with_template
from .interop_gen import generate_messages, _find_template_by_trigger, _normalize_validation_result
from api.activity_log import log_activity
from api.debug_log import log_debug_event
from api.metrics import record_event


def _log(event: str, **fields):
    log_debug_event(f"interop.{event}", **fields)

router = APIRouter()


@router.post("/api/interop/exec/{tool}")
async def run_tool(tool: str, request: Request):
    """
    Catch-all tool executor. Accept any body shape (JSON/form/multipart/query)
    and fail cleanly without raising FastAPI's JSON dict validator.
    """
    log_activity("tool.exec", tool=tool)
    try:
        ctype = (request.headers.get("content-type") or "").lower()
        raw = await request.body()
        if raw and "json" in ctype:
            _ = json.loads(raw.decode("utf-8"))
        elif raw:
            _ = parse_qs(raw.decode("utf-8", errors="ignore"))
        else:
            _ = await request.form()
    except Exception:
        pass
    raise HTTPException(status_code=404, detail=f"Unknown tool: {tool}")
templates = Jinja2Templates(directory="templates")
install_link_for(templates)
OUT_ROOT = Path("out/interop")
UI_OUT = OUT_ROOT / "ui"
INDEX_PATH = UI_OUT / "index.json"

DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")
for directory in (DEID_DIR, VAL_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def _load_template(directory: Path, name: str, kind: str) -> dict:
    path = directory / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"{kind.title()} template '{name}' not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed template
        raise HTTPException(status_code=400, detail=f"Invalid {kind} template JSON: {exc}") from exc


def load_deid_template(name: str) -> dict:
    return _load_template(DEID_DIR, name, "de-identify")


def load_validation_template(name: str) -> dict:
    return _load_template(VAL_DIR, name, "validation")


def _maybe_load_deid_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_deid_template(normalized)


def _maybe_load_validation_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    return load_validation_template(normalized)


def _maybe_load_deid_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    try:
        return load_deid_template(normalized)
    except FileNotFoundError:
        raise HTTPException(400, f"De-identify template '{normalized}' not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _maybe_load_validation_template(name: str | None) -> dict | None:
    if not name:
        return None
    normalized = str(name).strip()
    if not normalized or normalized.lower() in {"builtin", "legacy", "none"}:
        return None
    try:
        return load_validation_template(normalized)
    except FileNotFoundError:
        raise HTTPException(400, f"Validation template '{normalized}' not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


# -------- HL7 Sample Indexing (templates/hl7/*) ----------
SAMPLE_DIR = (Path(__file__).resolve().parent.parent / "templates" / "hl7").resolve()
VALID_VERSIONS = {"hl7-v2-3", "hl7-v2-4", "hl7-v2-5"}


def _derive_trigger_from_name(name: str) -> str:
    s = name
    if s.lower().endswith(".j2"):
        s = s[:-3]
    for ext in (".hl7", ".txt"):
        if s.lower().endswith(ext):
            s = s[: -len(ext)]
    return Path(s).stem.upper()


def _is_template_file(p: Path) -> bool:
    if not p.is_file():
        return False
    n = p.name.lower()
    return n.endswith(".hl7.j2") or n.endswith(".hl7") or n.endswith(".txt")

# ---- Trigger Description Library (CSV) ----
TRIGGER_CSV_PATH = SAMPLE_DIR / "trigger-events-v2.csv"
_TRIG_CACHE: Dict[str, Any] = {"mtime": None, "map": {}}


def _load_trigger_descriptions() -> Dict[str, str]:
    """Load trigger descriptions from CSV once, cached by mtime."""
    path = TRIGGER_CSV_PATH
    try:
        stat = path.stat()
    except Exception:
        return _TRIG_CACHE.get("map", {})
    if _TRIG_CACHE["mtime"] == stat.st_mtime:
        return _TRIG_CACHE["map"]

    mapping: Dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            rdr = csv.DictReader(line for line in fh if line.strip())
            cols = {c.lower(): c for c in rdr.fieldnames or []}
            code_col = None
            for cand in ("trigger", "event", "message", "code", "hl7_event", "hl7_trigger"):
                if cand in cols:
                    code_col = cols[cand]
                    break
            def_col = cols.get("definition") or cols.get("description")
            if code_col and def_col:
                for row in rdr:
                    code = (row.get(code_col) or "").strip().upper()
                    definition = (row.get(def_col) or "").strip()
                    if code:
                        mapping[code] = definition
    except Exception:
        mapping = {}
    _TRIG_CACHE["mtime"] = stat.st_mtime
    _TRIG_CACHE["map"] = mapping
    return mapping


def _describe_trigger(code: str) -> str:
    return _load_trigger_descriptions().get((code or "").upper(), "")

def _safe_sample_dir(version: str) -> Path:
    if version not in VALID_VERSIONS:
        raise HTTPException(status_code=400, detail=f"Unknown version '{version}'")
    p = (SAMPLE_DIR / version).resolve()
    if not str(p).startswith(str(SAMPLE_DIR)):
        # Path traversal protection
        raise HTTPException(status_code=400, detail="Invalid path")
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Version folder not found: {version}")
    return p


def _enumerate_samples(version: str, q: str | None = None, limit: int = 200) -> list[dict[str, str]]:
    """Return a list of {version, trigger, filename, relpath} dicts filtered by q.
    Supports *.hl7, *.hl7.j2, *.txt (case-insensitive)."""
    base = _safe_sample_dir(version)
    items: list[dict[str, str]] = []
    qnorm = (q or "").strip().lower()
    files = sorted([p for p in base.rglob("*") if _is_template_file(p)])
    for f in files:
        rel = f.relative_to(SAMPLE_DIR).as_posix()
        trigger = _derive_trigger_from_name(f.name)
        desc = _describe_trigger(trigger)
        if qnorm and qnorm not in f"{trigger} {rel} {desc}".lower():
            continue
        items.append({
            "version": version,
            "trigger": trigger,
            "description": desc,
            "filename": f.name,
            "relpath": rel,
        })
        if len(items) >= limit:
            break
    _log("samples.enumerated", version=version, query=q or "", limit=limit, returned=len(items))
    return items


def _assert_rel_under_templates(relpath: str) -> Path:
    p = (SAMPLE_DIR / relpath).resolve()
    if not str(p).startswith(str(SAMPLE_DIR)) or not p.exists() or not p.is_file():
        raise FileNotFoundError(relpath)
    return p


def _guess_rel_from_trigger(trigger: str, version: str = "hl7-v2-4") -> Optional[str]:
    """Find a template relpath for a trigger, checking the given version first then others."""
    cand = _find_template_by_trigger(version, trigger)
    if cand:
        return cand
    for v in sorted(VALID_VERSIONS):
        cand = _find_template_by_trigger(v, trigger)
        if cand:
            return cand
    return None


def _write_artifact(kind: str, data: dict) -> Path:
    data = {"kind": kind, **data}
    p = UI_OUT / kind / "active" / f"{int(time.time())}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


# ---------- Helpers ----------
def _find_newest_fhir_dir(base: Path) -> Optional[Path]:
    """Find the newest directory under base that contains FHIR json/ndjson files."""
    candidates = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".json", ".ndjson"}:
            candidates.append(p.parent)
    return max(set(candidates), key=lambda d: d.stat().st_mtime) if candidates else None


def _safe_json(o: Any) -> Any:
    try:
        return json.loads(o) if isinstance(o, str) else o
    except Exception:
        return {"ok": False, "error": "invalid json"}


@router.get("/api/interop/samples", response_class=JSONResponse)
def list_hl7_samples(
    version: str = Query("hl7-v2-4", description="One of hl7-v2-3|hl7-v2-4|hl7-v2-5"),
    q: str | None = Query(None, description="Search text for trigger/file"),
    limit: int = Query(200, ge=1, le=2000),
):
    """JSON list of sample entries for the UI to render."""
    _log("samples.list", version=version, query=q or "", limit=limit)
    try:
        data = _enumerate_samples(version, q=q, limit=limit)
    except HTTPException as exc:
        _log("samples.list.error", version=version, query=q or "", limit=limit, error=str(exc))
        data = []
    else:
        _log("samples.list.done", version=version, query=q or "", returned=len(data))
    return {"version": version, "count": len(data), "items": data}


@router.get("/api/interop/sample", response_class=PlainTextResponse)
def get_hl7_sample(relpath: str = Query(..., description="Relative path under templates/hl7")):
    """Return sample file text by relative path (e.g., 'hl7-v2-4/ADT_A01.hl7')."""
    _log("samples.fetch", relpath=relpath)
    try:
        p = _assert_rel_under_templates(relpath)
    except FileNotFoundError:
        _log("samples.fetch.missing", relpath=relpath)
        raise HTTPException(status_code=404, detail="Sample not found")
    text = p.read_text(encoding="utf-8", errors="ignore")
    _log("samples.fetch.done", relpath=relpath, bytes=len(text.encode("utf-8", errors="ignore")))
    return PlainTextResponse(text)


@router.get("/ui/interop/samples", response_class=HTMLResponse)
def render_hl7_samples_partial(
    request: Request,
    version: str = Query("hl7-v2-4"),
    q: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
):
    _log("samples.partial", version=version, query=q or "", limit=limit)
    try:
        items = _enumerate_samples(version, q=q, limit=limit)
    except HTTPException:
        items = []
        _log("samples.partial.error", version=version, query=q or "", limit=limit)
    else:
        _log("samples.partial.done", version=version, query=q or "", returned=len(items))
    return templates.TemplateResponse(
        "ui/interop/_sample_list.html",
        {"request": request, "items": items},
    )


@router.get("/api/interop/triggers", response_class=JSONResponse)
def triggers_json(version: str = Query("hl7-v2-4")):
    """JSON trigger list for typeahead; dedup by trigger."""
    _log("triggers.list", version=version)
    try:
        items = _enumerate_samples(version, q=None, limit=5000)
    except HTTPException:
        items = []
        _log("triggers.list.error", version=version)
    seen = set()
    out = []
    for it in items:
        trig = it["trigger"].upper()
        if trig in seen:
            continue
        seen.add(trig)
        out.append({
            "trigger": trig,
            "description": it.get("description", ""),
            "relpath": it.get("relpath", ""),
        })
    _log("triggers.list.done", version=version, returned=len(out))
    return {"version": version, "items": out}


@router.get("/ui/interop/triggers", response_class=HTMLResponse)
def render_trigger_options(
    request: Request,
    version: str = Query("hl7-v2-4"),
):
    """Returns <option> list for trigger selects based on templates/hl7/<version>."""
    _log("triggers.partial", version=version)
    try:
        raw = _enumerate_samples(version, q=None, limit=5000)
    except HTTPException:
        raw = []
        _log("triggers.partial.error", version=version)
    # Deduplicate and sort by trigger code
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for it in raw:
        trig = (it.get("trigger") or "").upper()
        if not trig or trig in seen:
            continue
        seen.add(trig)
        items.append({"trigger": trig, "description": it.get("description", "")})
    items = sorted(items, key=lambda x: x["trigger"])
    _log("triggers.partial.done", version=version, returned=len(items))
    return templates.TemplateResponse(
        "ui/interop/_trigger_options.html",
        {"request": request, "items": items},
    )


@router.post("/ui/interop/deidentify", response_class=HTMLResponse)
async def ui_deidentify(
    text: str = Form(...),
    seed: Optional[int] = Form(None),
    deid_template: Optional[str] = Form(None),
    apply_baseline: bool = Form(False),
):
    """
    HTML-friendly De-Identify: returns <pre> with scrubbed HL7 (no JSON body).
    """
    clean_seed = seed if seed not in ("", None) else None
    _log(
        "ui.deidentify",
        input_bytes=len((text or "").encode("utf-8", errors="ignore")),
        seed=clean_seed,
        template=deid_template or "",
        baseline=bool(apply_baseline),
    )
    tpl = _maybe_load_deid_template(deid_template)
    baseline_flag = bool(apply_baseline)
    if tpl or baseline_flag:
        template_payload = tpl or {"rules": []}
        out = apply_deid_with_template(text, template_payload, apply_baseline=baseline_flag)
    else:
        out = deidentify_message(text, seed=clean_seed)
    html = f"<pre class='codepane'>{_esc(out)}</pre>"
    _log("ui.deidentify.done", output_bytes=len(out.encode("utf-8", errors="ignore")))
    return HTMLResponse(html)


@router.post("/ui/interop/validate", response_class=HTMLResponse)
async def ui_validate(
    text: str = Form(...),
    profile: Optional[str] = Form(None),
    val_template: Optional[str] = Form(None),
):
    """
    HTML-friendly Validate: returns a small list of errors/warnings with OK/FAIL chip.
    """
    _log(
        "ui.validate",
        profile=profile or "",
        template=val_template or "",
        input_bytes=len((text or "").encode("utf-8", errors="ignore")),
    )
    start_ts = time.time()
    tpl = _maybe_load_validation_template(val_template)
    if tpl:
        res = validate_with_template(text, tpl)
    else:
        res = validate_message(text, profile=profile)
    elapsed_ms = int((time.time() - start_ts) * 1000)
    errors_list = list(res.get("errors", []) or [])
    warnings_list = list(res.get("warnings", []) or [])
    badge = "<span class='chip'>OK</span>" if res.get("ok") else "<span class='chip'>Issues</span>"
    errs = "".join(f"<li>{_esc(e)}</li>" for e in errors_list)
    warns = "".join(f"<li>{_esc(w)}</li>" for w in warnings_list)
    html = [
        f"<div>Result: {badge}</div>",
        "<div class='mt'><strong>Errors</strong><ul>" + (errs or "<li>None</li>") + "</ul></div>",
        "<div class='mt'><strong>Warnings</strong><ul class='muted'>" + (warns or "<li>None</li>") + "</ul></div>",
    ]
    _log(
        "ui.validate.done",
        ok=bool(res.get("ok")),
        errors=len(errors_list),
        warnings=len(warnings_list),
    )
    try:
        record_event(
            {
                "stage": "validate",
                "msg_id": str(uuid.uuid4()),
                "status": "success" if res.get("ok") else "fail",
                "elapsed_ms": elapsed_ms,
                "error_count": len(errors_list),
                "warning_count": len(warnings_list),
                "profile": profile or "",
            }
        )
    except Exception:
        _log("metrics.validate_record_failed")
    return HTMLResponse("".join(html))


@router.get("/api/interop/preview", response_class=HTMLResponse)
def api_preview(relpath: str = Query(...)):
    """
    Small HTML preview for a sample: used by the Finder to avoid raw JSON.
    """
    _log("samples.preview", relpath=relpath)
    try:
        p = _assert_rel_under_templates(relpath)
    except FileNotFoundError:
        _log("samples.preview.missing", relpath=relpath)
        raise HTTPException(status_code=404, detail="Sample not found")
    txt = p.read_text(encoding="utf-8", errors="ignore")
    _log("samples.preview.done", relpath=relpath, bytes=len(txt.encode("utf-8", errors="ignore")))
    return HTMLResponse(f"<pre class='codepane'>{_esc(txt)}</pre>")

@router.get("/interop/triggers/csv")
def download_trigger_csv():
    """Download the trigger description CSV (template created if missing)."""
    path = TRIGGER_CSV_PATH
    if not path.exists():
        # create minimal template
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            fh.write("Trigger,Definition\n")
    return StreamingResponse(path.open("rb"), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=trigger-events-v2.csv"})


@router.get("/ui/interop/trigger-admin", response_class=HTMLResponse)
def trigger_admin_panel(request: Request):
    mapping = _load_trigger_descriptions()
    items = [{"trigger": k, "description": v} for k, v in sorted(mapping.items())]
    return templates.TemplateResponse("ui/interop/_trigger_admin.html", {"request": request, "items": items})


def _save_trigger_descriptions(mapping: Dict[str, str]) -> None:
    TRIGGER_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRIGGER_CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Trigger", "Definition"])
        for k in sorted(mapping.keys()):
            writer.writerow([k, mapping[k]])
    # invalidate cache
    _TRIG_CACHE["mtime"] = None


@router.post("/interop/triggers/set")
def set_trigger_description(trigger: str = Form(...), description: str = Form("")):
    mapping = _load_trigger_descriptions().copy()
    mapping[trigger.upper()] = description.strip()
    _save_trigger_descriptions(mapping)
    return JSONResponse({"ok": True})

@router.post("/interop/hl7/draft-send")
async def interop_hl7_send(
    request: Request,
    message_type: str = Form(...),
    json_data: str = Form("{}"),
    host: str = Form(...),
    port: int = Form(...),
):
    try:
        data = json.loads(json_data) if json_data.strip() else {}
    except json.JSONDecodeError as e:
        payload = {"ok": False, "error": f"Invalid JSON for json_data: {e}"}
        _write_artifact("send", payload)
        return templates.TemplateResponse(
            "interop/partials/draft_result.html",
            {"request": request, "payload": payload},
            media_type="text/html",
        )
    message = draft_message(message_type, data)
    # Save temp HL7 for traceability
    hl7_path = UI_OUT / "draft" / "active" / f"{int(time.time())}.hl7"
    hl7_path.parent.mkdir(parents=True, exist_ok=True)
    hl7_path.write_text(message, encoding="utf-8")
    # Translate using trigger→map selection
    map_path = _pick_map_for_trigger(message_type)
    tr = _run_cli([
        "fhir",
        "translate",
        "--in",
        str(hl7_path),
        "--map",
        map_path,
        "--out",
        str(UI_OUT),
        "--message-mode",
    ])
    _write_artifact("translate", {**tr, "out": str(UI_OUT)})
    # send MLLP
    ack = await send_message(host, port, message)
    msa_aa = bool(re.search(r'(^|\r|\\r|\n)MSA\|AA(\||$)', ack or ""))
    payload = {
        "message_type": message_type,
        "message": message,
        "ack": ack,
        "ack_ok": msa_aa,
    }
    _write_artifact("send", payload)
    return templates.TemplateResponse(
        "interop/partials/draft_result.html",
        {"request": request, "payload": payload, "translate": tr},
        media_type="text/html",
    )


@router.post("/interop/hl7/analyze", response_class=HTMLResponse)
async def interop_hl7_analyze(request: Request, hl7_files: List[UploadFile] = File(...)):
    """Returns an HTML summary: per-file segment counts + simple validation warnings."""
    rows = []
    for up in hl7_files:
        text = (await up.read()).decode("utf-8", errors="ignore")
        segs: Dict[str, int] = {}
        for ln in text.splitlines():
            if not ln.strip():
                continue
            seg = ln.split("|", 1)[0].strip()
            if len(seg) == 3 and seg.isupper():
                segs[seg] = segs.get(seg, 0) + 1
        v = validate_message(text, profile=None)
        rows.append({"filename": up.filename, "segments": segs, "validation": v})
    return templates.TemplateResponse(
        "ui/interop/_analyze_result.html",
        {"request": request, "rows": rows},
    )


def _run_cli(args: List[str]) -> dict:
    proc = subprocess.run(
        ["python", "-m", "silhouette_core.cli", *args],
        capture_output=True,
        text=True,
    )
    return {"rc": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


@router.post("/interop/translate")
async def translate(
    request: Request,
    hl7_file: UploadFile = File(...),
    bundle: str = Form("transaction"),
    validate: bool = Form(False),
    out_dir: str = Form("out/interop/ui"),
):
    out_path = Path(out_dir)
    uploads = out_path / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    src = uploads / hl7_file.filename
    with src.open("wb") as fh:
        fh.write(hl7_file.file.read())
    args = ["fhir", "translate", "--in", str(src), "--bundle", bundle, "--out", out_dir]
    if validate:
        args.append("--validate")
    result = _run_cli(args)
    result["out"] = out_dir
    _write_artifact("translate", result)
    return templates.TemplateResponse(
        "interop/partials/translate_result.html",
        {"request": request, "result": result},
        media_type="text/html",
    )


@router.post("/interop/validate")
async def validate_fhir(
    request: Request,
    fhir_files: List[UploadFile] = File(...),
    out_dir: str = Form("out/interop/ui"),
):
    in_dir = Path(out_dir) / "uploads"
    in_dir.mkdir(parents=True, exist_ok=True)
    for up in fhir_files:
        dest = in_dir / up.filename
        with dest.open("wb") as fh:
            fh.write(up.file.read())
    args = ["fhir", "validate", "--in-dir", str(in_dir)]
    start_ts = time.time()
    result = _run_cli(args)
    result["out"] = out_dir
    _write_artifact("validate", result)
    try:
        record_event(
            {
                "stage": "validate",
                "msg_id": str(uuid.uuid4()),
                "status": "success" if int(result.get("rc", 1)) == 0 else "fail",
                "elapsed_ms": int((time.time() - start_ts) * 1000),
                "error_count": 0,
                "warning_count": 0,
                "profile": "cli",
            }
        )
    except Exception:
        _log("metrics.validate_record_failed")
    return templates.TemplateResponse(
        "interop/partials/validate_result.html",
        {"request": request, "result": result},
        media_type="text/html",
    )


# ---------- New: Send batch ----------
@router.post("/interop/hl7/send-batch", response_class=HTMLResponse)
async def interop_hl7_send_batch(
    request: Request,
    hl7_files: List[UploadFile] = File(...),
    host: str = Form(...),
    port: int = Form(...),
):
    results = []
    for up in hl7_files:
        msg = up.file.read().decode("utf-8", errors="ignore")
        ack = await send_message(host, port, msg)
        ok = bool(re.search(r'(^|\r|\\r|\n)MSA\|AA(\||$)', ack or ""))
        results.append({"name": up.filename, "ack_ok": ok})
    _write_artifact("send", {"batch": results})
    return templates.TemplateResponse(
        "interop/partials/draft_result.html",
        {"request": request, "payload": {"batch": results}},
        media_type="text/html",
    )


# ---------- New: Translate batch (+ optional chained validate) ----------
@router.post("/interop/translate-batch", response_class=HTMLResponse)
async def interop_translate_batch(
    request: Request,
    hl7_files: List[UploadFile] = File(...),
    bundle: str = Form("transaction"),
    out_dir: str = Form("out/interop/ui"),
    validate_after: bool = Form(False),
):
    uploads = Path(out_dir) / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    written = []
    for up in hl7_files:
        dest = uploads / up.filename
        dest.write_bytes(up.file.read())
        written.append(dest)
    for p in written:
        tr = _run_cli(["fhir", "translate", "--in", str(p), "--bundle", bundle, "--out", out_dir])
        _write_artifact("translate", {**tr, "file": p.name, "out": out_dir})
    val_res = None
    if validate_after:
        target_dir = _find_newest_fhir_dir(Path(out_dir)) or Path(out_dir)
        val_res = _run_cli(["fhir", "validate", "--in-dir", str(target_dir)])
        _write_artifact("validate", val_res)
    return templates.TemplateResponse(
        "interop/partials/pipeline_result.html",
        {
            "request": request,
            "trigger": "BATCH",
            "hl7_path": str(uploads),
            "translate": {"rc": 0, "stdout": f'Translated {len(written)} files', "stderr": ""},
            "validate": val_res or {"rc": 0, "stdout": "", "stderr": ""},
        },
        media_type="text/html",
    )


# ---------- New: Validate latest translate output ----------
@router.post("/interop/validate-last", response_class=HTMLResponse)
async def interop_validate_last(request: Request, out_dir: str = Form("out/interop/ui")):
    target_dir = _find_newest_fhir_dir(Path(out_dir))
    if not target_dir:
        return HTMLResponse("<div class='muted'>No recent FHIR outputs found to validate.</div>")
    start_ts = time.time()
    res = _run_cli(["fhir", "validate", "--in-dir", str(target_dir)])
    _write_artifact("validate", res)
    try:
        record_event(
            {
                "stage": "validate",
                "msg_id": str(uuid.uuid4()),
                "status": "success" if int(res.get("rc", 1)) == 0 else "fail",
                "elapsed_ms": int((time.time() - start_ts) * 1000),
                "error_count": 0,
                "warning_count": 0,
                "profile": "cli-latest",
            }
        )
    except Exception:
        _log("metrics.validate_record_failed")
    return templates.TemplateResponse(
        "interop/partials/validate_result.html",
        {"request": request, "result": res},
        media_type="text/html",
    )


# ---------- New: Simple HL7 analyze (segment counts) ----------
@router.post("/interop/hl7/analyze", response_class=HTMLResponse)
async def interop_hl7_analyze(
    request: Request,
    hl7_files: List[UploadFile] = File(...),
):
    sums: Dict[str, int] = {}
    for up in hl7_files:
        txt = up.file.read().decode("utf-8", errors="ignore")
        for line in txt.replace("\r", "\n").splitlines():
            if not line.strip():
                continue
            seg = line.split("|", 1)[0].strip()
            if 2 <= len(seg) <= 3 and seg.isalpha():
                sums[seg] = sums.get(seg, 0) + 1
    payload = {"segments": sums, "files": len(hl7_files)}
    _write_artifact("analyze", payload)
    return templates.TemplateResponse(
        "interop/partials/draft_result.html",
        {"request": request, "payload": payload},
        media_type="text/html",
    )


# ---------- New: Minimal directory watcher ----------
_WATCH_TASK: Optional[threading.Thread] = None
_WATCH_STOP = threading.Event()
_WATCH_CFG: Dict[str, str] = {}


def _watch_loop(in_dir: Path, out_dir: Path, bundle: str, validate_after: bool, poll_s: float = 2.0):
    in_dir.mkdir(parents=True, exist_ok=True)
    while not _WATCH_STOP.is_set():
        for p in sorted(in_dir.glob("*.hl7")):
            try:
                tr = _run_cli(["fhir", "translate", "--in", str(p), "--bundle", bundle, "--out", str(out_dir)])
                _write_artifact("translate", {**tr, "file": p.name, "out": str(out_dir)})
                if validate_after:
                    target = _find_newest_fhir_dir(out_dir) or out_dir
                    va = _run_cli(["fhir", "validate", "--in-dir", str(target)])
                    _write_artifact("validate", va)
                p.rename(p.with_suffix(".done"))
            except Exception as e:  # pragma: no cover - best effort
                _write_artifact("translate", {"rc": 1, "stderr": str(e), "file": p.name})
        _WATCH_STOP.wait(poll_s)


@router.post("/interop/watch/start")
async def interop_watch_start(
    in_dir: str = Form("in/hl7"),
    out_dir: str = Form("out/interop/watch"),
    bundle: str = Form("transaction"),
    validate_after: bool = Form(False),
):
    global _WATCH_TASK, _WATCH_CFG
    if _WATCH_TASK and _WATCH_TASK.is_alive():
        return JSONResponse({"ok": False, "error": "watcher already running", "cfg": _WATCH_CFG})
    _WATCH_STOP.clear()
    _WATCH_CFG = {
        "in_dir": in_dir,
        "out_dir": out_dir,
        "bundle": bundle,
        "validate_after": bool(validate_after),
    }
    t = threading.Thread(
        target=_watch_loop,
        args=(Path(in_dir), Path(out_dir), bundle, bool(validate_after)),
        daemon=True,
    )
    _WATCH_TASK = t
    t.start()
    return JSONResponse({"ok": True, "cfg": _WATCH_CFG})


@router.post("/interop/watch/stop")
async def interop_watch_stop():
    _WATCH_STOP.set()
    return JSONResponse({"ok": True})


@router.get("/interop/watch/status")
async def interop_watch_status():
    running = bool(_WATCH_TASK and _WATCH_TASK.is_alive())
    return JSONResponse({"running": running, "cfg": _WATCH_CFG})


# ---------- New: Minimal FHIR-read helper ----------
@router.post("/interop/fhir/read", response_class=HTMLResponse)
async def interop_fhir_read(
    request: Request,
    base: str = Form(...),
    resource: str = Form(...),
    token: str = Form(""),
):
    if not requests:
        return HTMLResponse("<div class='muted'>requests not installed; cannot read from FHIR API.</div>")
    headers = {"Accept": "application/fhir+json"}
    if token.strip():
        headers["Authorization"] = f"Bearer {token.strip()}"
    url = f"{base.rstrip('/')}/{resource.lstrip('/')}"
    r = requests.get(url, headers=headers, timeout=20)
    payload = {"status": r.status_code, "body": _safe_json(r.text)}
    return templates.TemplateResponse(
        "interop/partials/draft_result.html",
        {"request": request, "payload": payload},
        media_type="text/html",
    )


# ---------- Summary, Demo & Quickstart ----------


@router.get("/interop/summary", response_class=HTMLResponse)
def interop_summary():
    html = (
        "<section class='card'>"
        "<h3>Interop Metrics</h3>"
        "<p class='muted'>Detailed KPIs now live on the dedicated Reports dashboard.</p>"
        "<div class='mt'><a class='btn' href='/reports'>Open Reports</a></div>"
        "</section>"
    )
    return HTMLResponse(html)


@router.post("/interop/demo/seed", response_class=HTMLResponse)
def interop_demo_seed():
    html = (
        "<div class='muted'>"
        "Pick a version and trigger, then click <strong>Run Pipeline</strong> to preview a sample."
        "</div>"
    )
    return HTMLResponse(html)


@router.post("/interop/quickstart", response_class=HTMLResponse)
async def interop_quickstart(
    request: Request,
    trigger: str = Form(...),
    version: str = Form("hl7-v2-4"),
    seed: str = Form("1337"),
    ensure_unique: str = Form("true"),
    include_clinical: str = Form("true"),
    deidentify: str = Form("false"),
):
    """
    Demo pipeline:
      1) Generate one HL7 message from templates with deterministic seed
      2) Translate HL7 ➜ FHIR using silhouette CLI if available
      3) Validate HL7 (placeholder workbook)
      4) Render 3-column HTML result (HL7, FHIR, Validation)
    """
    version = (version or "hl7-v2-4").strip()
    rel = _guess_rel_from_trigger(trigger.strip(), version)
    if not rel:
        return HTMLResponse(
            f"<div class='error'>No sample found for <code>{trigger}</code>.</div>",
            status_code=404,
        )
    try:
        p = _assert_rel_under_templates(rel)
        template_text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return HTMLResponse("<div class='error'>{\"detail\":\"Not Found\"}</div>", status_code=404)

    try:
        base_seed = int(seed)
    except Exception:
        base_seed = 1337

    msg = template_text
    if ensure_unique.lower() in ("1", "true", "yes", "on"):
        msg = ensure_unique_fields(msg, index=0, seed=base_seed)
    if include_clinical.lower() in ("1", "true", "yes", "on"):
        msg = enrich_clinical_fields(msg, seed=base_seed)
    if deidentify.lower() in ("1", "true", "yes", "on"):
        msg = deidentify_message(msg, seed=base_seed)

    fhir_json, translate_note = _hl7_to_fhir_via_cli(msg, trigger=trigger)
    val = validate_message(msg, profile=None)
    val_html = _render_validation(val)

    html = (
        "<div class='grid' style='grid-template-columns: 1fr 1fr 1fr; gap:12px;'>"
        "<section class='card'>"
        f"<h4>HL7 — {trigger} <small class='chip'>{version}</small></h4>"
        "<pre class='codepane' style='white-space:pre-wrap;'>"
        f"{_esc(msg)}"
        "</pre>"
        "</section>"
        "<section class='card'>"
        "<h4>FHIR (Preview)</h4>"
        f"<div class='muted' style='margin-bottom:6px;'>{_esc(translate_note)}</div>"
        "<pre class='codepane' style='white-space:pre-wrap;'>"
        f"{_esc(fhir_json)}"
        "</pre>"
        "</section>"
        "<section class='card'>"
        "<h4>Validation</h4>"
        f"{val_html}"
        "</section>"
        "</div>"
    )
    return HTMLResponse(html)

# -------------------- helpers for quickstart pipeline --------------------

# Trigger → Map selection
MAP_INDEX: Dict[str, str] = {
    # Admissions / ADT family
    "ADT_A01": "maps/adt_uscore.yaml",
    "ADT_A04": "maps/adt_uscore.yaml",
    "ADT_A08": "maps/adt_update_uscore.yaml",
    "ADT_A28": "maps/adt_others_uscore.yaml",
    "ADT_A31": "maps/adt_merge_uscore.yaml",
    # Orders / results
    "ORM_O01": "maps/orm_uscore.yaml",
    "ORU_R01": "maps/oru_uscore.yaml",
    "OMX_*": "maps/omx_uscore.yaml",
    "ORX_*": "maps/orx_uscore.yaml",
    # Medications
    "RDE_O11": "maps/rde_uscore.yaml",
    # Immunizations
    "VXU_V04": "maps/vxu_uscore.yaml",
    # Master file / documents
    "MDM_T02": "maps/mdm_uscore.yaml",
    # Scheduling
    "SIU_S12": "maps/siu_uscore.yaml",
    # Billing / coverage
    "DFT_P03": "maps/dft_uscore.yaml",
    "BAR_P01": "maps/bar_uscore.yaml",
    "COVERAGE": "maps/coverage_uscore.yaml",
    # Research / additional resources
    "RESEARCH_*": "maps/research_uscore.yaml",
    # Misc fallback
    "MISC_*": "maps/misc_noresource_uscore.yaml",
}

def _pick_map_for_trigger(trigger: str) -> str:
    t=(trigger or '').upper()
    if t in MAP_INDEX:
        return MAP_INDEX[t]
    for key,val in MAP_INDEX.items():
        if key.endswith('*') and t.startswith(key[:-1]):
            return val
    return 'maps/adt_uscore.yaml'

def _hl7_to_fhir_via_cli(hl7_text: str, trigger: str = '') -> tuple[str, str]:
    """Backward-compatible wrapper using _translate_hl7_to_fhir_cli.

    Returns (stdout, note) where ``note`` includes the selected map path so callers
    can confirm which mapping was chosen even if the CLI is missing.
    """
    tmp_dir = Path(tempfile.gettempdir()) / "silhouette_qs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    map_path = _pick_map_for_trigger(trigger) if trigger else None
    res = _translate_hl7_to_fhir_cli(hl7_text, tmp_dir)
    note = res.get("stderr", "") or ""
    if map_path:
        note = f"{note}\n(using map {map_path})".strip()
    out = res.get("stdout", "") or "{}"
    return (out, note)

def _esc(s: str) -> str:
    return s.replace("<", "&lt;").replace(">", "&gt;")


def _render_validation(result: Dict[str, Any]) -> str:
    ok = bool(result.get("ok"))
    errs = result.get("errors") or []
    warns = result.get("warnings") or []
    badge = (
        "<span class='chip' style='background:#e6ffe6;border:1px solid #b2e5b2;'>OK</span>"
        if ok
        else "<span class='chip' style='background:#ffecec;border:1px solid #f5b1b1;'>FAIL</span>"
    )
    parts = [f"<div>Result: {badge}</div>"]
    if errs:
        parts.append("<div class='mt'><strong>Errors</strong><ul>")
        for e in errs:
            parts.append(f"<li>{_esc(str(e))}</li>")
        parts.append("</ul></div>")
    if warns:
        parts.append("<div class='mt'><strong>Warnings</strong><ul class='muted'>")
        for w in warns:
            parts.append(f"<li>{_esc(str(w))}</li>")
        parts.append("</ul></div>")
    return "".join(parts)


# -------- Pipeline helpers --------

def _now_tag() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

def _write_file(dir_: Path, name: str, data: str | bytes, binary=False) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    p = dir_ / name
    mode = "wb" if binary else "w"
    enc = None if binary else "utf-8"
    with p.open(mode, encoding=enc) as fh:
        fh.write(data)
    return p

def _translate_hl7_to_fhir_cli(hl7_text: str, out_dir: Path) -> dict:
    """Best-effort HL7→FHIR via CLI. Falls back gracefully if CLI isn't available."""
    tmp_in = out_dir / "input.hl7"
    _write_file(out_dir, "input.hl7", hl7_text)
    cmd = ["silhouette", "fhir", "translate", "--in", str(tmp_in), "--out", str(out_dir), "--message-mode", "--dry-run"]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
        _write_file(out_dir, "translate.stdout.txt", cp.stdout or "")
        _write_file(out_dir, "translate.stderr.txt", cp.stderr or "")
        ok = cp.returncode == 0
        fhir_paths = list(out_dir.glob("*.ndjson")) + list(out_dir.glob("*.json"))
        if fhir_paths:
            return {"ok": ok, "paths": [p.as_posix() for p in fhir_paths], "stdout": cp.stdout, "stderr": cp.stderr}
        if cp.stdout.strip():
            _write_file(out_dir, "translated.bundle.json", cp.stdout)
            return {"ok": ok, "paths": [(out_dir / "translated.bundle.json").as_posix()], "stdout": cp.stdout, "stderr": cp.stderr}
        return {"ok": ok, "paths": [], "stdout": cp.stdout, "stderr": cp.stderr}
    except FileNotFoundError:
        return {"ok": False, "paths": [], "stdout": "", "stderr": "silhouette CLI not found; install or adjust PATH"}

def _post_fhir(paths: list[Path], url: str) -> tuple[bool, list[str]]:
    if not requests:
        return False, ["requests not available in this environment"]
    results = []
    ok = True
    for p in paths:
        data = p.read_text(encoding="utf-8", errors="ignore")
        try:
            r = requests.post(url, data=data, headers={"Content-Type": "application/fhir+json"})
            results.append(f"{p.name} → {r.status_code}")
            ok = ok and (200 <= r.status_code < 300)
        except Exception as e:
            results.append(f"{p.name} → ERROR {e}")
            ok = False
    return ok, results

def _render_pipeline_result(hl7_txt: str, val: dict, trans: dict, post_res: dict | None, artifacts: Path) -> HTMLResponse:
    normalized = _normalize_validation_result(val, hl7_txt)
    issues = normalized.get("issues", [])
    errs = "".join(
        f"<li>{_esc(it.get('location') or it.get('code') or '—')}: {_esc(it.get('message') or '')}</li>"
        for it in issues
        if str(it.get("severity", "")).lower() == "error"
    )
    warns = "".join(
        f"<li class='muted'>{_esc(it.get('location') or it.get('code') or '—')}: {_esc(it.get('message') or '')}</li>"
        for it in issues
        if str(it.get("severity", "")).lower() == "warning"
    )
    fhir_list = "".join(
        f"<li><a href='/ui/interop/history/view?path={_esc(p)}' target='_blank'>{_esc(Path(p).name)}</a></li>"
        for p in trans.get("paths", [])
    )
    post_blk = ""
    if post_res is not None:
        post_items = "".join(f"<li>{_esc(x)}</li>" for x in (post_res.get("lines") or []))
        post_badge = "<span class='chip'>OK</span>" if post_res.get("ok") else "<span class='chip'>Failed</span>"
        post_blk = f"<div class='mt'><strong>Send FHIR</strong> {post_badge}<ul>{post_items or '<li>None</li>'}</ul></div>"
    html = f"""
    <div class='card'>
      <h3>Pipeline Result</h3>
      <div class='mt'><strong>Input HL7</strong></div>
      <pre class='codepane'>{_esc(hl7_txt[:15000])}</pre>
      <div class='mt'><strong>Analyze</strong> {"<span class='chip'>OK</span>" if val.get("ok") else "<span class='chip'>Issues</span>"}
        <div class='grid2'>
          <div><em>Errors</em><ul>{errs or '<li>None</li>'}</ul></div>
          <div><em>Warnings</em><ul class='muted'>{warns or '<li>None</li>'}</ul></div>
        </div>
      </div>
      <div class='mt'><strong>Translate (HL7→FHIR)</strong> {"<span class='chip'>OK</span>" if trans.get("ok") else "<span class='chip'>Issues</span>"}
        <ul>{fhir_list or '<li>No emitted files (see translate.stderr.txt)</li>'}</ul>
      </div>
      {post_blk}
      <div class='mt muted'>Artifacts: <code>{_esc(artifacts.as_posix())}</code></div>
    </div>
    """
    return HTMLResponse(textwrap.dedent(html))

@router.post("/api/interop/pipeline/run", response_class=HTMLResponse)
async def run_pipeline(request: Request):
    """Robust pipeline runner that accepts JSON or form submissions."""
    from urllib.parse import parse_qs

    ctype = (request.headers.get("content-type") or "").lower()
    raw = await request.body()
    body: dict[str, Any] = {}

    if raw and "json" in ctype:
        try:
            parsed = json.loads(raw.decode("utf-8"))
            if isinstance(parsed, dict):
                body = parsed
        except Exception:
            body = {}

    if not body and raw:
        try:
            q = parse_qs(raw.decode("utf-8", errors="ignore"))
            body = {k: v[-1] for k, v in q.items()} if q else {}
        except Exception:
            body = {}

    if not body:
        try:
            form = await request.form()
            body = {k: form.get(k) for k in form.keys()} if form else {}
        except Exception:
            body = {}

    if not body:
        qp = request.query_params
        body = {k: qp.get(k) for k in qp.keys()}

    def _to_bool(v: Any, default: bool = False) -> bool:
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        return str(v).lower() in {"1", "true", "on", "yes"}

    def _to_int(v: Any) -> int | None:
        try:
            return int(v)
        except Exception:
            return None

    version = body.get("version", "hl7-v2-4")
    trigger = body.get("trigger")
    template_relpath = body.get("template_relpath")
    text = body.get("text")
    seed = _to_int(body.get("seed"))
    ensure_unique = _to_bool(body.get("ensure_unique"), True)
    include_clinical = _to_bool(body.get("include_clinical"), False)
    deidentify = _to_bool(body.get("deidentify"), False)
    apply_baseline = _to_bool(body.get("apply_baseline"), False)
    post_fhir = _to_bool(body.get("post_fhir"), False)
    fhir_endpoint = body.get("fhir_endpoint")
    deid_template_name = body.get("deid_template")
    val_template_name = body.get("val_template")

    log_activity(
        "pipeline.run",
        steps=len(body.get("steps", [])) if isinstance(body.get("steps"), list) else 0,
        dry_run=bool(body.get("dry_run")),
    )

    if version not in VALID_VERSIONS:
        raise HTTPException(400, f"Unknown version '{version}'")
    if not text:
        body2 = {
            "version": version,
            "template_relpath": template_relpath,
            "trigger": trigger,
            "count": 1,
            "seed": seed,
            "ensure_unique": ensure_unique,
            "include_clinical": include_clinical,
            "deidentify": deidentify,
            "apply_baseline": apply_baseline,
            "deid_template": deid_template_name,
        }
        resp = generate_messages(body2)
        text = resp.body.decode("utf-8") if hasattr(resp, "body") else str(resp)
    if not text or not text.strip():
        raise HTTPException(400, "No HL7 content to process")

    deid_template = _maybe_load_deid_template(deid_template_name)
    if deidentify:
        if deid_template or apply_baseline:
            tpl_payload = deid_template or {"rules": []}
            text = apply_deid_with_template(text, tpl_payload, apply_baseline=apply_baseline)
        else:
            text = deidentify_message(text, seed=seed)

    run_dir = OUT_ROOT / "pipeline" / _now_tag()
    _write_file(run_dir, "input.hl7", text)

    tpl_val = _maybe_load_validation_template(val_template_name)
    if tpl_val:
        val = validate_with_template(text, tpl_val)
    else:
        val = validate_message(text, profile=None)
    _write_file(run_dir, "validate.json", json.dumps(val, indent=2))

    trans = _translate_hl7_to_fhir_cli(text, run_dir)
    _write_file(run_dir, "translate.meta.json", json.dumps({"ok": trans.get("ok"), "paths": trans.get("paths")}, indent=2))

    post_result = None
    if post_fhir and trans.get("paths"):
        paths = [Path(p) for p in trans["paths"]]
        if fhir_endpoint:
            ok, lines = _post_fhir(paths, fhir_endpoint)
            post_result = {"ok": ok, "lines": lines}
        else:
            post_result = {"ok": False, "lines": ["No endpoint specified (dummy server disabled in this build)."]}

    return _render_pipeline_result(text, val, trans, post_result, run_dir)

# -------- In-app dummy FHIR endpoint (for local testing) --------
FHIR_DUMMY_OUT = Path("out/fhir/dummy")

@router.post("/api/fhir/dummy", response_class=HTMLResponse)
async def fhir_dummy(request: Request):
    """Accept FHIR payloads and save them for inspection."""
    payload = await request.body()
    FHIR_DUMMY_OUT.mkdir(parents=True, exist_ok=True)
    name = f"{_now_tag()}.json"
    path = FHIR_DUMMY_OUT / name
    try:
        path.write_bytes(payload)
        size = len(payload or b"")
        return HTMLResponse(f"<div class='muted'>Dummy FHIR accepted <code>{_esc(name)}</code> ({size} bytes).</div>")
    except Exception as e:
        return HTMLResponse(f"<div class='error'>Failed to write payload: {_esc(str(e))}</div>", status_code=500)
