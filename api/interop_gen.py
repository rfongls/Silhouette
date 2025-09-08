from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Literal, Optional
import re

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from silhouette_core.interop.hl7_mutate import (
    enrich_clinical_fields,
    ensure_unique_fields,
    load_template_text,
)
from silhouette_core.interop.deid import deidentify_message
from silhouette_core.interop.mllp import send_mllp_batch
from silhouette_core.interop.validate_workbook import validate_message

router = APIRouter()

TEMPLATES_HL7_DIR = (Path(__file__).resolve().parent.parent / "templates" / "hl7").resolve()
VALID_VERSIONS = {"hl7-v2-3", "hl7-v2-4", "hl7-v2-5"}


def _assert_rel_under_templates(relpath: str) -> Path:
    p = (TEMPLATES_HL7_DIR / relpath).resolve()
    if not str(p).startswith(str(TEMPLATES_HL7_DIR)):
        raise HTTPException(status_code=400, detail="Invalid relpath")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail=f"Template not found: {relpath}")
    return p


@router.post("/api/interop/generate", response_model=None)
def generate_messages(body: dict = Body(...)):
    version = body.get("version", "hl7-v2-4")
    if version not in VALID_VERSIONS:
        raise HTTPException(400, f"Unknown version '{version}'")

    rel = body.get("template_relpath")
    trig = (body.get("trigger") or "").strip()
    text = body.get("text")
    if not rel and trig:
        t = trig.upper()
        cand = f"{version}/{t}.hl7"
        p = (TEMPLATES_HL7_DIR / cand).resolve()
        if p.exists():
            rel = cand
    if not rel and not text:
        raise HTTPException(400, "Provide template_relpath or text")
    if rel and not rel.startswith(version + "/"):
        raise HTTPException(400, "template_relpath must live under the selected version folder")

    count = int(body.get("count", 1))
    if count < 1 or count > 10000:
        raise HTTPException(400, "count must be 1..10000")

    seed = body.get("seed")
    rng_seed = int(seed) if seed is not None else None
    ensure_unique = bool(body.get("ensure_unique", True))
    include_clinical = bool(body.get("include_clinical", False))
    deidentify = bool(body.get("deidentify", False))
    output_format: Literal["single", "one_per_file", "ndjson", "zip"] = body.get("output_format", "single")

    template_text = text or load_template_text(_assert_rel_under_templates(rel))

    msgs: list[str] = []
    for i in range(count):
        msg = template_text
        derived = None
        if rng_seed is not None:
            h = hashlib.sha256(f"{rng_seed}|{rel or 'inline'}|{i}".encode()).hexdigest()
            derived = int(h[:12], 16)

        if ensure_unique:
            msg = ensure_unique_fields(msg, index=i, seed=derived)
        if include_clinical:
            msg = enrich_clinical_fields(msg, seed=derived)
        if deidentify:
            msg = deidentify_message(msg, seed=derived)
        msgs.append(msg)

    if output_format == "single":
        body = "\n".join(msgs)
        return PlainTextResponse(body, media_type="text/plain")
    elif output_format == "ndjson":
        lines = [json.dumps({"i": i, "hl7": m}, ensure_ascii=False) for i, m in enumerate(msgs)]
        return PlainTextResponse("\n".join(lines), media_type="application/x-ndjson")
    elif output_format in ("one_per_file", "zip"):
        mem = BytesIO()
        with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
            for i, m in enumerate(msgs):
                name = f"msg_{i:05d}.hl7"
                z.writestr(name, m)
        mem.seek(0)
        headers = {"Content-Disposition": 'attachment; filename="generated_messages.zip"'}
        return StreamingResponse(mem, media_type="application/zip", headers=headers)
    else:
        raise HTTPException(400, "Unknown output_format")


@router.post("/api/interop/deidentify")
def api_deidentify(text: str = Body(..., embed=True), seed: Optional[int] = Body(None)):
    out = deidentify_message(text, seed=seed)
    return JSONResponse({"text": out})


@router.post("/api/interop/validate")
def api_validate(text: str = Body(..., embed=True), profile: Optional[str] = Body(None)):
    results = validate_message(text, profile=profile)
    return JSONResponse(results)


@router.post("/api/interop/mllp/send")
def api_mllp_send(
    host: str = Body(...),
    port: int = Body(...),
    messages: list[str] | str = Body(..., embed=True),
    timeout: float = Body(5.0),
):
    if isinstance(messages, str):
        chunks = re.split(r"\r?\n\s*\r?\n", messages)
        messages = [m.strip() for m in chunks if m.strip()]
        if not messages:
            raise HTTPException(status_code=400, detail="No messages parsed from input string")
    acks = send_mllp_batch(host, port, messages, timeout=timeout)
    return JSONResponse({"sent": len(messages), "acks": acks})
