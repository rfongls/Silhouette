from __future__ import annotations
import csv
import json
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.templating import Jinja2Templates

try:
    from api.ui import install_link_for
except Exception:  # pragma: no cover - fallback when helper unavailable
    def install_link_for(_):  # type: ignore[misc]
        pass

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR = Path("configs/interop/validate_templates")
for folder in (DEID_DIR, VAL_DIR):
    folder.mkdir(parents=True, exist_ok=True)


@dataclass
class DeidRule:
    segment: str
    field: int
    component: Optional[int] = None
    subcomponent: Optional[int] = None
    action: str = "redact"
    param: Optional[str] = None


@dataclass
class DeidTemplate:
    name: str
    version: str = "v1"
    rules: List[DeidRule] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "rules": [asdict(r) for r in (self.rules or [])],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DeidTemplate":
        return DeidTemplate(
            name=data.get("name", "unnamed"),
            version=data.get("version", "v1"),
            rules=[DeidRule(**row) for row in data.get("rules", [])],
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
    checks: List[ValidateCheck] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "checks": [asdict(c) for c in (self.checks or [])],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ValidateTemplate":
        return ValidateTemplate(
            name=data.get("name", "unnamed"),
            version=data.get("version", "v1"),
            checks=[ValidateCheck(**row) for row in data.get("checks", [])],
        )


def _safe_name(name: str) -> str:
    cleaned = "".join(c for c in (name or "") if c.isalnum() or c in {"-", "_"}).strip()
    return cleaned or "default"


def _json_path(base: Path, name: str) -> Path:
    return base / f"{_safe_name(name)}.json"


def _list_templates(base: Path) -> List[str]:
    return [p.stem for p in sorted(base.glob("*.json"))]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Template not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@router.get("/ui/settings/ping", name="ui_settings_ping")
def ui_settings_ping() -> Dict[str, bool]:
    return {"ok": True}


@router.get("/ui/settings", response_class=HTMLResponse, name="ui_settings_index")
def ui_settings_index(request: Request) -> HTMLResponse | PlainTextResponse:
    try:
        return templates.TemplateResponse(
            "ui/settings/index.html",
            {
                "request": request,
                "deid_templates": _list_templates(DEID_DIR),
                "val_templates": _list_templates(VAL_DIR),
            },
        )
    except Exception:
        return PlainTextResponse(
            "Settings template render failed:\n\n" + traceback.format_exc(),
            status_code=500,
        )


@router.post("/ui/settings/deid/create", response_class=HTMLResponse, name="ui_settings_deid_create")
def ui_settings_deid_create(request: Request, name: str = Form(...)) -> HTMLResponse:
    path = _json_path(DEID_DIR, name)
    if path.exists():
        raise HTTPException(status_code=400, detail="Template already exists")
    tpl = DeidTemplate(name=_safe_name(name), rules=[])
    _save_json(path, tpl.to_dict())
    return templates.TemplateResponse(
        "ui/settings/_deid_list.html",
        {"request": request, "names": _list_templates(DEID_DIR)},
    )


@router.get("/ui/settings/deid/edit/{name}", response_class=HTMLResponse, name="ui_settings_deid_edit")
def ui_settings_deid_edit(request: Request, name: str) -> HTMLResponse:
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    return templates.TemplateResponse("ui/settings/deid_edit.html", {"request": request, "tpl": tpl})


@router.post("/ui/settings/deid/add_rule/{name}", response_class=HTMLResponse, name="ui_settings_deid_add_rule")
def ui_settings_deid_add_rule(
    request: Request,
    name: str,
    segment: str = Form(...),
    field: int = Form(...),
    component: Optional[int] = Form(None),
    subcomponent: Optional[int] = Form(None),
    action: str = Form("redact"),
    param: Optional[str] = Form(None),
) -> HTMLResponse:
    path = _json_path(DEID_DIR, name)
    tpl = DeidTemplate.from_dict(_load_json(path))
    tpl.rules = tpl.rules or []
    tpl.rules.append(
        DeidRule(
            segment=segment.strip().upper(),
            field=int(field),
            component=component if component not in (None, "") else None,
            subcomponent=subcomponent if subcomponent not in (None, "") else None,
            action=(action or "redact").strip(),
            param=param or None,
        )
    )
    _save_json(path, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})


@router.post("/ui/settings/deid/delete_rule/{name}", response_class=HTMLResponse, name="ui_settings_deid_delete_rule")
def ui_settings_deid_delete_rule(request: Request, name: str, index: int = Form(...)) -> HTMLResponse:
    path = _json_path(DEID_DIR, name)
    tpl = DeidTemplate.from_dict(_load_json(path))
    tpl.rules = tpl.rules or []
    if 0 <= index < len(tpl.rules):
        del tpl.rules[index]
    _save_json(path, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})


@router.get("/ui/settings/deid/export/{name}.json", response_class=JSONResponse, name="ui_settings_deid_export_json")
def ui_settings_deid_export_json(name: str) -> JSONResponse:
    return JSONResponse(_load_json(_json_path(DEID_DIR, name)))


@router.get("/ui/settings/deid/export/{name}.csv", response_class=PlainTextResponse, name="ui_settings_deid_export_csv")
def ui_settings_deid_export_csv(name: str) -> PlainTextResponse:
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    rows = ["segment,field,component,subcomponent,action,param"]
    for rule in tpl.rules or []:
        rows.append(
            ",".join(
                [
                    rule.segment,
                    str(rule.field),
                    "" if rule.component is None else str(rule.component),
                    "" if rule.subcomponent is None else str(rule.subcomponent),
                    rule.action,
                    "" if rule.param is None else rule.param,
                ]
            )
        )
    return PlainTextResponse("\n".join(rows), media_type="text/csv")


@router.post("/ui/settings/deid/import_csv/{name}", response_class=HTMLResponse, name="ui_settings_deid_import_csv")
async def ui_settings_deid_import_csv(request: Request, name: str, file: UploadFile = File(...)) -> HTMLResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    rows = (await file.read()).decode("utf-8").splitlines()
    reader = csv.DictReader(rows)
    rules: List[DeidRule] = []
    for row in reader:
        rules.append(
            DeidRule(
                segment=(row.get("segment") or "").strip().upper(),
                field=int(row.get("field") or 0),
                component=int(row["component"]) if row.get("component") else None,
                subcomponent=int(row["subcomponent"]) if row.get("subcomponent") else None,
                action=(row.get("action") or "redact").strip(),
                param=row.get("param") or None,
            )
        )
    tpl = DeidTemplate(name=_safe_name(name), rules=rules)
    _save_json(_json_path(DEID_DIR, name), tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})


@router.post("/ui/settings/val/create", response_class=HTMLResponse, name="ui_settings_val_create")
def ui_settings_val_create(request: Request, name: str = Form(...)) -> HTMLResponse:
    path = _json_path(VAL_DIR, name)
    if path.exists():
        raise HTTPException(status_code=400, detail="Template already exists")
    tpl = ValidateTemplate(name=_safe_name(name), checks=[])
    _save_json(path, tpl.to_dict())
    return templates.TemplateResponse(
        "ui/settings/_val_list.html",
        {"request": request, "names": _list_templates(VAL_DIR)},
    )


@router.get("/ui/settings/val/edit/{name}", response_class=HTMLResponse, name="ui_settings_val_edit")
def ui_settings_val_edit(request: Request, name: str) -> HTMLResponse:
    tpl = ValidateTemplate.from_dict(_load_json(_json_path(VAL_DIR, name)))
    return templates.TemplateResponse("ui/settings/val_edit.html", {"request": request, "tpl": tpl})


@router.post("/ui/settings/val/add_check/{name}", response_class=HTMLResponse, name="ui_settings_val_add_check")
def ui_settings_val_add_check(
    request: Request,
    name: str,
    segment: str = Form(...),
    field: int = Form(...),
    required: bool = Form(False),
    pattern: Optional[str] = Form(None),
    allowed_values: Optional[str] = Form(None),
) -> HTMLResponse:
    path = _json_path(VAL_DIR, name)
    tpl = ValidateTemplate.from_dict(_load_json(path))
    tpl.checks = tpl.checks or []
    allowed = [v.strip() for v in (allowed_values or "").replace(";", ",").split(",") if v.strip()] or None
    tpl.checks.append(
        ValidateCheck(
            segment=segment.strip().upper(),
            field=int(field),
            required=bool(required),
            pattern=pattern or None,
            allowed_values=allowed,
        )
    )
    _save_json(path, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_val_checks_table.html", {"request": request, "tpl": tpl})


@router.post("/ui/settings/val/delete_check/{name}", response_class=HTMLResponse, name="ui_settings_val_delete_check")
def ui_settings_val_delete_check(request: Request, name: str, index: int = Form(...)) -> HTMLResponse:
    path = _json_path(VAL_DIR, name)
    tpl = ValidateTemplate.from_dict(_load_json(path))
    tpl.checks = tpl.checks or []
    if 0 <= index < len(tpl.checks):
        del tpl.checks[index]
    _save_json(path, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_val_checks_table.html", {"request": request, "tpl": tpl})


@router.get("/ui/settings/val/export/{name}.json", response_class=JSONResponse, name="ui_settings_val_export_json")
def ui_settings_val_export_json(name: str) -> JSONResponse:
    return JSONResponse(_load_json(_json_path(VAL_DIR, name)))


@router.get("/ui/settings/val/export/{name}.csv", response_class=PlainTextResponse, name="ui_settings_val_export_csv")
def ui_settings_val_export_csv(name: str) -> PlainTextResponse:
    tpl = ValidateTemplate.from_dict(_load_json(_json_path(VAL_DIR, name)))
    rows = ["segment,field,required,pattern,allowed_values"]
    for check in tpl.checks or []:
        rows.append(
            ",".join(
                [
                    check.segment,
                    str(check.field),
                    "true" if check.required else "false",
                    "" if not check.pattern else check.pattern.replace(",", ";"),
                    "" if not check.allowed_values else ";".join(check.allowed_values),
                ]
            )
        )
    return PlainTextResponse("\n".join(rows), media_type="text/csv")


@router.post("/ui/settings/val/import_csv/{name}", response_class=HTMLResponse, name="ui_settings_val_import_csv")
async def ui_settings_val_import_csv(request: Request, name: str, file: UploadFile = File(...)) -> HTMLResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    rows = (await file.read()).decode("utf-8").splitlines()
    reader = csv.DictReader(rows)
    checks: List[ValidateCheck] = []
    for row in reader:
        allowed_raw = row.get("allowed_values") or ""
        allowed = [v.strip() for v in allowed_raw.replace(";", ",").split(",") if v.strip()] or None
        checks.append(
            ValidateCheck(
                segment=(row.get("segment") or "").strip().upper(),
                field=int(row.get("field") or 0),
                required=str(row.get("required") or "true").strip().lower() in {"1", "true", "yes", "y"},
                pattern=row.get("pattern") or None,
                allowed_values=allowed,
            )
        )
    tpl = ValidateTemplate(name=_safe_name(name), checks=checks)
    _save_json(_json_path(VAL_DIR, name), tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_val_checks_table.html", {"request": request, "tpl": tpl})
