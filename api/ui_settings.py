from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.templating import Jinja2Templates

# If you have a helper to add template globals, import it; otherwise this no-ops.
try:
    from api.ui import install_link_for
except Exception:
    def install_link_for(_):  # no-op fallback
        pass

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

# Storage roots
DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR  = Path("configs/interop/validate_templates")
for d in (DEID_DIR, VAL_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------- Models ----------
@dataclass
class DeidRule:
    segment: str
    field: int
    component: Optional[int] = None
    subcomponent: Optional[int] = None
    action: str = "redact"  # redact | mask | hash | replace | preset
    param: Optional[str] = None

@dataclass
class DeidTemplate:
    name: str
    version: str = "v1"
    rules: List[DeidRule] = None
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "version": self.version, "rules": [asdict(r) for r in (self.rules or [])]}
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DeidTemplate":
        return DeidTemplate(
            name=d.get("name", "unnamed"),
            version=d.get("version", "v1"),
            rules=[DeidRule(**r) for r in d.get("rules", [])],
        )

@dataclass
class ValidateCheck:
    segment: str
    field: int
    required: bool = True
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None

@dataclass
class ValidateTemplate:
    name: str
    version: str = "v1"
    checks: List[ValidateCheck] = None
    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "version": self.version, "checks": [asdict(c) for c in (self.checks or [])]}
    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ValidateTemplate":
        return ValidateTemplate(
            name=d.get("name", "unnamed"),
            version=d.get("version", "v1"),
            checks=[ValidateCheck(**c) for c in d.get("checks", [])],
        )

# ---------- Helpers ----------
def _safe_name(name: str) -> str:
    s = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")).strip()
    return s or "default"

def _json_path(base: Path, name: str) -> Path:
    return base / f"{_safe_name(name)}.json"

def _list_templates(base: Path) -> List[str]:
    return [p.stem for p in sorted(base.glob("*.json"))]

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))

def _save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# ---------- Pages ----------
@router.get("/ui/settings", response_class=HTMLResponse, name="ui_settings_index", response_model=None)
def ui_settings_index(request: Request) -> Response:
    # Ensure 'default' exists for De-ID on first visit, without overwriting
    default_path = _json_path(DEID_DIR, "default")
    if not default_path.exists():
        _save_json(default_path, {"name": "default", "version": "v1", "rules": []})
    return templates.TemplateResponse(
        "ui/settings/index.html",
        {
            "request": request,
            "deid_templates": _list_templates(DEID_DIR),
            "val_templates": _list_templates(VAL_DIR),
        },
    )

# ---------- De-ID: create / edit / add / delete rule / import-export ----------
@router.post("/ui/settings/deid/create", response_class=HTMLResponse, name="ui_settings_deid_create", response_model=None)
def ui_settings_deid_create(request: Request, name: str = Form(...)) -> Response:
    p = _json_path(DEID_DIR, name)
    if p.exists():
        raise HTTPException(status_code=400, detail="Template already exists")
    _save_json(p, DeidTemplate(name=_safe_name(name), rules=[]).to_dict())
    # Return the list partial (HTMX swap target is #deid-list)
    return templates.TemplateResponse(
        "ui/settings/_deid_list.html",
        {"request": request, "deid_templates": _list_templates(DEID_DIR)},
    )

@router.get("/ui/settings/deid/edit/{name}", response_class=HTMLResponse, name="ui_settings_deid_edit", response_model=None)
def ui_settings_deid_edit(request: Request, name: str) -> Response:
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    return templates.TemplateResponse("ui/settings/deid_edit.html", {"request": request, "tpl": tpl})

@router.post("/ui/settings/deid/add_rule/{name}", response_class=HTMLResponse, name="ui_settings_deid_add_rule", response_model=None)
def ui_settings_deid_add_rule(
    request: Request,
    name: str,
    segment: str = Form(...),
    field: int = Form(...),
    component: Optional[int] = Form(None),
    subcomponent: Optional[int] = Form(None),
    action: str = Form("redact"),
    param: Optional[str] = Form(None),
) -> Response:
    p = _json_path(DEID_DIR, name)
    tpl = DeidTemplate.from_dict(_load_json(p))
    tpl.rules = tpl.rules or []
    tpl.rules.append(
        DeidRule(
            segment=segment.strip().upper(),
            field=int(field),
            component=component if component not in (None, "") else None,
            subcomponent=subcomponent if subcomponent not in (None, "") else None,
            action=action,
            param=param or None,
        )
    )
    _save_json(p, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})

@router.post("/ui/settings/deid/delete_rule/{name}", response_class=HTMLResponse, name="ui_settings_deid_delete_rule", response_model=None)
def ui_settings_deid_delete_rule(request: Request, name: str, index: int = Form(...)) -> Response:
    p = _json_path(DEID_DIR, name)
    tpl = DeidTemplate.from_dict(_load_json(p))
    if 0 <= index < len(tpl.rules or []):
        del tpl.rules[index]
    _save_json(p, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})

@router.get("/ui/settings/deid/export/{name}.json", response_class=JSONResponse, name="ui_settings_deid_export_json")
def ui_settings_deid_export_json(name: str):
    return JSONResponse(_load_json(_json_path(DEID_DIR, name)))

@router.get("/ui/settings/deid/export/{name}.csv", response_class=PlainTextResponse, name="ui_settings_deid_export_csv")
def ui_settings_deid_export_csv(name: str):
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    out = ["segment,field,component,subcomponent,action,param"]
    for r in tpl.rules or []:
        out.append(",".join([
            r.segment,
            str(r.field),
            "" if r.component is None else str(r.component),
            "" if r.subcomponent is None else str(r.subcomponent),
            r.action,
            "" if r.param is None else r.param,
        ]))
    return PlainTextResponse("\n".join(out), media_type="text/csv")

@router.post("/ui/settings/deid/import_csv/{name}", response_class=HTMLResponse, name="ui_settings_deid_import_csv", response_model=None)
async def ui_settings_deid_import_csv(request: Request, name: str, file: UploadFile = File(...)) -> Response:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    rows = (await file.read()).decode("utf-8").splitlines()
    reader = csv.DictReader(rows)
    rules: List[DeidRule] = []
    for row in reader:
        rules.append(DeidRule(
            segment=(row.get("segment") or "").strip().upper(),
            field=int(row.get("field") or 0),
            component=int(row["component"]) if row.get("component") else None,
            subcomponent=int(row["subcomponent"]) if row.get("subcomponent") else None,
            action=(row.get("action") or "redact").strip(),
            param=row.get("param") or None,
        ))
    _save_json(_json_path(DEID_DIR, name), DeidTemplate(name=_safe_name(name), rules=rules).to_dict())
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})


@router.post("/ui/settings/deid/seed_defaults/{name}", response_class=HTMLResponse, name="ui_settings_deid_seed_defaults", response_model=None)
def ui_settings_deid_seed_defaults(request: Request, name: str) -> Response:
    """
    Create or overwrite a template with a rich baseline of rules using presets.
    """
    # A carefully chosen baseline across common PHI fields (can expand later)
    baseline_rules = [
        # PID
        {"segment": "PID", "field": 5, "component": 1, "action": "preset", "param": "name"},  # Patient Name (family^given)
        {"segment": "PID", "field": 7, "action": "preset", "param": "birthdate"},
        {"segment": "PID", "field": 8, "action": "preset", "param": "gender"},
        {"segment": "PID", "field": 11, "action": "preset", "param": "address"},
        {"segment": "PID", "field": 13, "action": "preset", "param": "phone"},
        {"segment": "PID", "field": 14, "action": "preset", "param": "phone"},
        {"segment": "PID", "field": 15, "action": "preset", "param": "language"},
        {"segment": "PID", "field": 19, "action": "preset", "param": "ssn"},

        # NK1
        {"segment": "NK1", "field": 2, "action": "preset", "param": "name"},
        {"segment": "NK1", "field": 4, "action": "preset", "param": "address"},
        {"segment": "NK1", "field": 5, "action": "preset", "param": "phone"},
        {"segment": "NK1", "field": 6, "action": "preset", "param": "phone"},

        # PV1
        {"segment": "PV1", "field": 1, "action": "replace", "param": "1"},
        {"segment": "PV1", "field": 7, "action": "preset", "param": "name"},
        {"segment": "PV1", "field": 8, "action": "preset", "param": "name"},
        {"segment": "PV1", "field": 9, "action": "preset", "param": "name"},
        {"segment": "PV1", "field": 19, "action": "preset", "param": "name"},
        {"segment": "PV1", "field": 39, "action": "preset", "param": "facility"},

        # PD1
        {"segment": "PD1", "field": 5, "action": "preset", "param": "name"},
        {"segment": "PD1", "field": 7, "action": "preset", "param": "facility"},

        # ORC/OBR/OBX timestamps & contact
        {"segment": "ORC", "field": 9, "action": "preset", "param": "datetime"},
        {"segment": "ORC", "field": 15, "action": "preset", "param": "datetime"},
        {"segment": "OBR", "field": 6, "action": "preset", "param": "datetime"},
        {"segment": "OBR", "field": 7, "action": "preset", "param": "datetime"},
        {"segment": "OBR", "field": 8, "action": "preset", "param": "datetime"},
        {"segment": "OBR", "field": 14, "action": "preset", "param": "datetime"},
        {"segment": "OBR", "field": 17, "action": "preset", "param": "phone"},
        {"segment": "OBR", "field": 22, "action": "preset", "param": "datetime"},
        {"segment": "OBX", "field": 14, "action": "preset", "param": "datetime"},

        # OBX blobs (PDF/XML)
        {"segment": "OBX", "field": 5, "action": "preset", "param": "pdf_blob"},

        # NTE free text
        {"segment": "NTE", "field": 3, "action": "preset", "param": "note"},

        # EVN / ACC dates
        {"segment": "EVN", "field": 2, "action": "preset", "param": "datetime"},
        {"segment": "EVN", "field": 3, "action": "preset", "param": "datetime"},
        {"segment": "ACC", "field": 1, "action": "preset", "param": "datetime"},
        {"segment": "ACC", "field": 4, "action": "preset", "param": "datetime"},
    ]

    path = _json_path(DEID_DIR, name)
    _save_json(path, {"name": _safe_name(name), "version": "v1", "rules": baseline_rules})
    tpl = DeidTemplate.from_dict(_load_json(path))
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})

# Delete the entire De-ID template (required by your template)
@router.post("/ui/settings/deid/delete", name="ui_settings_deid_delete", response_class=HTMLResponse, response_model=None)
def ui_settings_deid_delete(request: Request, name: str = Form(...)) -> Response:
    p = _json_path(DEID_DIR, name)
    if p.exists():
        p.unlink()
    return templates.TemplateResponse(
        "ui/settings/_deid_list.html",
        {"request": request, "deid_templates": _list_templates(DEID_DIR)},
    )

# ---------- Validate: create / edit / add / delete check / import-export ----------
@router.post("/ui/settings/val/create", response_class=HTMLResponse, name="ui_settings_val_create", response_model=None)
def ui_settings_val_create(request: Request, name: str = Form(...)) -> Response:
    p = _json_path(VAL_DIR, name)
    if p.exists():
        raise HTTPException(status_code=400, detail="Template already exists")
    _save_json(p, ValidateTemplate(name=_safe_name(name), checks=[]).to_dict())
    return templates.TemplateResponse(
        "ui/settings/_val_list.html",
        {"request": request, "val_templates": _list_templates(VAL_DIR)},
    )

@router.get("/ui/settings/val/edit/{name}", response_class=HTMLResponse, name="ui_settings_val_edit", response_model=None)
def ui_settings_val_edit(request: Request, name: str) -> Response:
    tpl = ValidateTemplate.from_dict(_load_json(_json_path(VAL_DIR, name)))
    return templates.TemplateResponse("ui/settings/val_edit.html", {"request": request, "tpl": tpl})

@router.post("/ui/settings/val/add_check/{name}", response_class=HTMLResponse, name="ui_settings_val_add_check", response_model=None)
def ui_settings_val_add_check(
    request: Request,
    name: str,
    segment: str = Form(...),
    field: int = Form(...),
    required: bool = Form(False),
    pattern: Optional[str] = Form(None),
    allowed_values: Optional[str] = Form(None),  # comma- or semicolon-separated
) -> Response:
    p = _json_path(VAL_DIR, name)
    tpl = ValidateTemplate.from_dict(_load_json(p))
    tpl.checks = tpl.checks or []
    allowed = [v.strip() for v in (allowed_values or "").replace(";", ",").split(",") if v.strip()] or None
    tpl.checks.append(ValidateCheck(
        segment=segment.strip().upper(),
        field=int(field),
        required=bool(required),
        pattern=pattern or None,
        allowed_values=allowed,
    ))
    _save_json(p, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_val_checks_table.html", {"request": request, "tpl": tpl})

@router.post("/ui/settings/val/delete_check/{name}", response_class=HTMLResponse, name="ui_settings_val_delete_check", response_model=None)
def ui_settings_val_delete_check(request: Request, name: str, index: int = Form(...)) -> Response:
    p = _json_path(VAL_DIR, name)
    tpl = ValidateTemplate.from_dict(_load_json(p))
    if 0 <= index < len(tpl.checks or []):
        del tpl.checks[index]
    _save_json(p, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_val_checks_table.html", {"request": request, "tpl": tpl})

@router.get("/ui/settings/val/export/{name}.json", response_class=JSONResponse, name="ui_settings_val_export_json")
def ui_settings_val_export_json(name: str):
    return JSONResponse(_load_json(_json_path(VAL_DIR, name)))

@router.get("/ui/settings/val/export/{name}.csv", response_class=PlainTextResponse, name="ui_settings_val_export_csv")
def ui_settings_val_export_csv(name: str):
    tpl = ValidateTemplate.from_dict(_load_json(_json_path(VAL_DIR, name)))
    out = ["segment,field,required,pattern,allowed_values"]
    for c in tpl.checks or []:
        out.append(",".join([
            c.segment,
            str(c.field),
            "true" if c.required else "false",
            "" if not c.pattern else c.pattern.replace(",", ";"),
            "" if not c.allowed_values else ";".join(c.allowed_values),
        ]))
    return PlainTextResponse("\n".join(out), media_type="text/csv")

@router.post("/ui/settings/val/import_csv/{name}", response_class=HTMLResponse, name="ui_settings_val_import_csv", response_model=None)
async def ui_settings_val_import_csv(request: Request, name: str, file: UploadFile = File(...)) -> Response:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    rows = (await file.read()).decode("utf-8").splitlines()
    reader = csv.DictReader(rows)
    checks: List[ValidateCheck] = []
    for row in reader:
        allowed_raw = row.get("allowed_values") or ""
        allowed = [v.strip() for v in allowed_raw.replace(";", ",").split(",") if v.strip()] or None
        checks.append(ValidateCheck(
            segment=(row.get("segment") or "").strip().upper(),
            field=int(row.get("field") or 0),
            required=(str(row.get("required") or "true").strip().lower() in ("1", "true", "yes", "y")),
            pattern=row.get("pattern") or None,
            allowed_values=allowed,
        ))
    _save_json(_json_path(VAL_DIR, name), ValidateTemplate(name=_safe_name(name), checks=checks).to_dict())
    tpl = ValidateTemplate.from_dict(_load_json(_json_path(VAL_DIR, name)))
    return templates.TemplateResponse("ui/settings/_val_checks_table.html", {"request": request, "tpl": tpl})

# Delete the entire Validate template (required by your template)
@router.post("/ui/settings/val/delete", name="ui_settings_val_delete", response_class=HTMLResponse, response_model=None)
def ui_settings_val_delete(request: Request, name: str = Form(...)) -> Response:
    p = _json_path(VAL_DIR, name)
    if p.exists():
        p.unlink()
    return templates.TemplateResponse(
        "ui/settings/_val_list.html",
        {"request": request, "val_templates": _list_templates(VAL_DIR)},
    )
