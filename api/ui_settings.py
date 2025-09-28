from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.templating import Jinja2Templates

from api.debug_log import log_debug_event, is_debug_enabled

# If you have a helper to add template globals, import it; otherwise this no-ops.
try:
    from api.ui import install_link_for
except Exception:
    def install_link_for(_):  # no-op fallback
        pass

router = APIRouter()
templates = Jinja2Templates(directory="templates")
install_link_for(templates)

# ------------------------------
# Test & Preview helpers
# ------------------------------


def _detect_hl7_separators(text: str) -> tuple[str, str, str]:
    """Return (field_sep, component_sep, subcomponent_sep)."""

    field_sep, comp_sep, sub_sep = "|", "^", "&"
    for raw in (text or "").splitlines():
        if raw.startswith("MSH"):
            field_sep = raw[3] if len(raw) > 3 else field_sep
            parts = raw.split(field_sep)
            encoding_chars = parts[1] if len(parts) > 1 else "^~\\&"
            comp_sep = encoding_chars[0] if len(encoding_chars) > 0 else comp_sep
            sub_sep = encoding_chars[3] if len(encoding_chars) > 3 else sub_sep
            break
    return field_sep, comp_sep, sub_sep


def _apply_action(
    value: str,
    action: str,
    param_mode: Optional[str],
    param_preset: Optional[str],
    param_free: Optional[str],
    pattern: Optional[str],
    repl: Optional[str],
) -> str:
    normalized_action = (action or "redact").strip().lower()
    value = value or ""

    if normalized_action == "redact":
        return "[REDACTED]"
    if normalized_action == "replace":
        return repl or ""
    if normalized_action == "mask":
        mask_char = (param_free or "*")[0]
        return "".join(mask_char if ch.isalnum() else ch for ch in value)
    if normalized_action == "hash":
        salt = param_free or ""
        return hashlib.sha256((salt + value).encode("utf-8")).hexdigest()[:16]
    if normalized_action == "regex_redact":
        return re.sub(pattern or "", "", value) if pattern else value
    if normalized_action == "regex_replace":
        return re.sub(pattern or "", repl or "", value) if pattern else value
    if normalized_action == "preset":
        mode = (param_mode or "preset").strip().lower()
        if mode == "free":
            return param_free or ""
        presets = {
            "name": "JANE^DOE",
            "birthdate": "19700101",
            "datetime": "19700101120000",
            "gender": "U",
            "address": "123 MAIN ST",
            "phone": "5551234567",
            "language": "ENG",
            "race": "OT",
            "mrn": "000000",
            "ssn": "000-00-0000",
            "facility": "HOSPITAL",
            "note": "[SYNTHETIC NOTE]",
            "pdf_blob": "[SYNTHETIC PDF]",
            "xml_blob": "[SYNTHETIC XML]",
        }
        key = (param_preset or "").strip().lower()
        return presets.get(key, "")

    return value

# Storage roots
DEID_DIR = Path("configs/interop/deid_templates")
VAL_DIR  = Path("configs/interop/validate_templates")
for d in (DEID_DIR, VAL_DIR):
    d.mkdir(parents=True, exist_ok=True)

PRESET_PARAM_OPTIONS = [
    "name",
    "birthdate",
    "datetime",
    "gender",
    "address",
    "phone",
    "language",
    "race",
    "mrn",
    "ssn",
    "facility",
    "note",
    "pdf_blob",
    "xml_blob",
]
PRESET_PARAM_KEYS = set(PRESET_PARAM_OPTIONS)
DEFAULT_PRESET_KEY = PRESET_PARAM_OPTIONS[0]

ACTION_ALIASES = {
    "replace (literal)": "replace",
    "preset (synthetic)": "preset",
    "regex redact": "regex_redact",
    "regex replace": "regex_replace",
}


def _normalize_action(action: Optional[str]) -> str:
    raw = (action or "redact").strip().lower()
    raw = raw.replace("-", "_")
    normalized = ACTION_ALIASES.get(raw, raw.replace(" ", "_"))
    return normalized or "redact"


def _initial_param_state(action: Optional[str], param: Optional[str]) -> Dict[str, str]:
    normalized_action = _normalize_action(action)
    state = {
        "mode": "preset",
        "param_preset": DEFAULT_PRESET_KEY,
        "param_free": "",
        "pattern": "",
        "repl": "",
    }

    if not param:
        return state

    value = str(param)
    if normalized_action == "preset":
        if value in PRESET_PARAM_KEYS:
            state["param_preset"] = value
        else:
            state["mode"] = "free"
            state["param_free"] = value
    elif normalized_action in {"replace", "mask", "hash"}:
        state["param_free"] = value
    elif normalized_action == "regex_redact":
        state["pattern"] = value
    elif normalized_action == "regex_replace":
        parsed: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(value)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            state["pattern"] = str(parsed.get("pattern") or "")
            state["repl"] = str(parsed.get("repl") or "")
        elif ":::" in value:
            pattern_val, repl_val = value.split(":::", 1)
            state["pattern"] = pattern_val
            state["repl"] = repl_val
        else:
            state["pattern"] = value
    return state


def _build_rule_modal_context(request: Request, tpl: "DeidTemplate", clone: Optional["DeidRule"]):
    action_value = _normalize_action(clone.action if clone else "redact")
    initial_state = _initial_param_state(action_value, getattr(clone, "param", None))
    return {
        "request": request,
        "tpl": tpl,
        "clone": clone,
        "initial_action": action_value,
        "initial_param_mode": initial_state["mode"],
        "initial_param_preset": initial_state["param_preset"],
        "initial_param_free": initial_state["param_free"],
        "initial_pattern": initial_state["pattern"],
        "initial_repl": initial_state["repl"],
        "preset_options": PRESET_PARAM_OPTIONS,
    }

ACTION_ALIASES = {
    "replace (literal)": "replace",
    "preset (synthetic)": "preset",
    "regex redact": "regex_redact",
    "regex replace": "regex_replace",
}


def _normalize_action(action: Optional[str]) -> str:
    raw = (action or "redact").strip().lower()
    raw = raw.replace("-", "_")
    normalized = ACTION_ALIASES.get(raw, raw.replace(" ", "_"))
    return normalized or "redact"

# ---------- Models ----------
@dataclass
class DeidRule:
    segment: str
    field: int
    component: Optional[int] = None
    subcomponent: Optional[int] = None
    action: str = "redact"  # redact | mask | hash | replace | preset | regex_replace | regex_redact | dotnet_regex_*
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


def _canonical_key(rule: Dict[str, Any]) -> tuple[Any, ...]:
    """Return a tuple that uniquely identifies a rule ignoring param values."""

    component = rule.get("component")
    if isinstance(component, str) and component.isdigit():
        component_val: Optional[int] = int(component)
    elif isinstance(component, int):
        component_val = component
    else:
        component_val = None

    subcomponent = rule.get("subcomponent")
    if isinstance(subcomponent, str) and subcomponent.isdigit():
        subcomponent_val: Optional[int] = int(subcomponent)
    elif isinstance(subcomponent, int):
        subcomponent_val = subcomponent
    else:
        subcomponent_val = None

    return (
        (rule.get("segment") or "").strip().upper(),
        int(rule.get("field") or 0),
        component_val,
        subcomponent_val,
        (rule.get("action") or "redact").strip(),
    )


def _has_duplicate(rules: List[Dict[str, Any]], new_rule: Dict[str, Any]) -> bool:
    new_key = _canonical_key(new_rule)
    for rule in rules or []:
        if _canonical_key(rule) == new_key:
            return True
    return False


def _build_rule_prefill(rule: Optional[DeidRule]) -> Dict[str, Any]:
    prefill: Dict[str, Any] = {
        "segment": "" if rule is None else (rule.segment or ""),
        "field": "" if rule is None else str(rule.field if rule.field is not None else ""),
        "component": "" if rule is None or rule.component is None else str(rule.component),
        "subcomponent": "" if rule is None or rule.subcomponent is None else str(rule.subcomponent),
        "action": "redact" if rule is None else (rule.action or "redact"),
        "param_mode": "preset",
        "preset_value": DEFAULT_PRESET_KEY,
        "free_value": "",
        "regex_pattern": "",
        "regex_repl": "",
        "regex_flags": "",
    }
    prefill["regex_param_json"] = json.dumps({"pattern": "", "repl": "", "flags": ""})

    if rule is None:
        return prefill

    action = prefill["action"]
    raw_param = rule.param or ""
    param_mode = "preset"

    if action in {"mask", "hash", "replace"}:
        param_mode = "free"
        prefill["free_value"] = raw_param
    elif action in {"regex_replace", "regex_redact", "dotnet_regex_replace", "dotnet_regex_redact"}:
        param_mode = "regex"
        pattern = raw_param
        repl = ""
        flags = ""
        if isinstance(raw_param, str) and raw_param.strip().startswith("{"):
            try:
                obj = json.loads(raw_param)
                pattern = str(obj.get("pattern") or "")
                repl = str(obj.get("repl") or "")
                flags = str(obj.get("flags") or "").lower()
            except Exception:
                pattern = raw_param
        prefill["regex_pattern"] = pattern
        prefill["regex_repl"] = repl
        prefill["regex_flags"] = flags
        prefill["regex_param_json"] = json.dumps({
            "pattern": pattern or "",
            "repl": repl or "",
            "flags": flags or "",
        })
    elif action == "preset":
        if raw_param and raw_param not in PRESET_PARAM_KEYS:
            param_mode = "free"
            prefill["free_value"] = raw_param
        else:
            prefill["preset_value"] = raw_param or DEFAULT_PRESET_KEY
    else:
        if raw_param:
            param_mode = "free"
            prefill["free_value"] = raw_param

    if param_mode != "preset":
        # Ensure presets fall back to default when switching modes later
        prefill.setdefault("preset_value", DEFAULT_PRESET_KEY)

    if param_mode != "free" and not prefill.get("free_value"):
        prefill["free_value"] = ""

    if param_mode != "regex" and not prefill.get("regex_param_json"):
        prefill["regex_param_json"] = json.dumps({"pattern": "", "repl": "", "flags": ""})

    if param_mode not in {"preset", "free"}:
        param_mode = "preset"

    prefill["param_mode"] = param_mode
    return prefill


@router.post("/api/tools/deid/test_rule", name="api_deid_test_rule")
def api_deid_test_rule(payload: Dict[str, Any] = Body(...)) -> JSONResponse:
    """Apply the selected action to a single HL7 field/component for preview."""

    text = payload.get("text") or ""
    segment = (payload.get("segment") or "").strip().upper()
    try:
        field = int(payload.get("field") or 0)
    except (TypeError, ValueError):
        field = 0
    component_raw = payload.get("component")
    try:
        component = int(component_raw) if component_raw not in (None, "", 0) else None
    except (TypeError, ValueError):
        component = None
    sub_raw = payload.get("subcomponent")
    try:
        subcomponent = int(sub_raw) if sub_raw not in (None, "", 0) else None
    except (TypeError, ValueError):
        subcomponent = None
    action = (payload.get("action") or "redact").strip().lower()
    param_mode = payload.get("param_mode")
    param_preset = payload.get("param_preset")
    param_free = payload.get("param_free")
    pattern = payload.get("pattern")
    repl = payload.get("repl")

    if not text.strip():
        return JSONResponse({"ok": False, "error": "empty_text"}, status_code=400)
    if not segment or field <= 0:
        return JSONResponse({"ok": False, "error": "segment_and_field_required"}, status_code=400)

    field_sep, comp_sep, sub_sep = _detect_hl7_separators(text)
    lines = (text or "").splitlines()
    seg_index: Optional[int] = None
    for idx, raw in enumerate(lines):
        if raw.startswith(segment):
            seg_index = idx
            break
    if seg_index is None:
        for idx, raw in enumerate(lines):
            if raw.strip():
                seg_index = idx
                break
    if seg_index is None:
        return JSONResponse({"ok": False, "error": "no_lines"}, status_code=400)

    before_line = lines[seg_index]
    fields = before_line.split(field_sep)
    token_index = field if segment != "MSH" else field - 1

    before_field = ""
    after_field = ""

    try:
        if 0 <= token_index < len(fields):
            raw_field = fields[token_index]
            if component:
                components = raw_field.split(comp_sep)
                if 1 <= component <= len(components):
                    comp_value = components[component - 1]
                    if subcomponent:
                        subcomponents = comp_value.split(sub_sep)
                        if 1 <= subcomponent <= len(subcomponents):
                            before_field = subcomponents[subcomponent - 1]
                            subcomponents[subcomponent - 1] = _apply_action(
                                before_field,
                                action,
                                param_mode,
                                param_preset,
                                param_free,
                                pattern,
                                repl,
                            )
                            components[component - 1] = sub_sep.join(subcomponents)
                            fields[token_index] = comp_sep.join(components)
                            after_field = subcomponents[subcomponent - 1]
                    else:
                        before_field = comp_value
                        components[component - 1] = _apply_action(
                            comp_value,
                            action,
                            param_mode,
                            param_preset,
                            param_free,
                            pattern,
                            repl,
                        )
                        fields[token_index] = comp_sep.join(components)
                        after_field = components[component - 1]
            else:
                before_field = raw_field
                fields[token_index] = _apply_action(
                    raw_field,
                    action,
                    param_mode,
                    param_preset,
                    param_free,
                    pattern,
                    repl,
                )
                after_field = fields[token_index]

        after_line = field_sep.join(fields)
        lines[seg_index] = after_line
    except Exception as exc:
        return JSONResponse({"ok": False, "error": "exception", "detail": str(exc)}, status_code=500)

    return JSONResponse(
        {
            "ok": True,
            "path": f"{segment}:{field}" + (f".{component}" if component else "") + (f".{subcomponent}" if subcomponent else ""),
            "before": {
                "field": before_field,
                "line": before_line,
                "message": "\r".join((text or "").splitlines()),
            },
            "after": {
                "field": after_field,
                "line": lines[seg_index],
                "message": "\r".join(lines),
            },
        }
    )

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
    # Return the select partial (HTMX target is #deid-select-wrap)
    return templates.TemplateResponse(
        "ui/settings/_deid_select_inner.html",
        {"request": request, "deid_templates": _list_templates(DEID_DIR)},
    )

@router.get("/ui/settings/deid/edit/{name}", response_class=HTMLResponse, name="ui_settings_deid_edit", response_model=None)
def ui_settings_deid_edit(request: Request, name: str) -> Response:
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    return templates.TemplateResponse("ui/settings/deid_edit.html", {"request": request, "tpl": tpl})


@router.get(
    "/ui/settings/deid/new_rule_modal/{name}",
    response_class=HTMLResponse,
    name="ui_settings_deid_new_rule_modal",
    response_model=None,
)
def ui_settings_deid_new_rule_modal(request: Request, name: str) -> Response:
    tpl = DeidTemplate.from_dict(_load_json(_json_path(DEID_DIR, name)))
    return templates.TemplateResponse(
        "ui/settings/_deid_rule_modal.html",
        _build_rule_modal_context(request, tpl, None),
    )

@router.get(
    "/ui/settings/deid/param_controls",
    response_class=HTMLResponse,
    name="ui_settings_deid_param_controls",
    response_model=None,
)
def ui_settings_deid_param_controls(
    request: Request,
    action: Optional[str] = None,
    param_mode: Optional[str] = None,
    param_preset: Optional[str] = None,
    param_free: Optional[str] = None,
    pattern: Optional[str] = None,
    repl: Optional[str] = None,
    initial_param_mode: Optional[str] = None,
    initial_param_preset: Optional[str] = None,
    initial_param_free: Optional[str] = None,
    initial_pattern: Optional[str] = None,
    initial_repl: Optional[str] = None,
) -> Response:
    params = request.query_params

    if is_debug_enabled():
        try:
            log_debug_event(
                "deid:param_controls_request",
                path=str(request.url),
                method=request.method,
                query=dict(request.query_params.multi_items()),
                action=action,
                param_mode=param_mode,
                param_preset=param_preset,
                param_free=param_free,
                pattern=pattern,
                repl=repl,
                initial_param_mode=initial_param_mode,
                initial_param_preset=initial_param_preset,
                initial_param_free=initial_param_free,
                initial_pattern=initial_pattern,
                initial_repl=initial_repl,
            )
        except Exception:
            pass

    def _last_value(key: str, *fallbacks: Optional[str]) -> Optional[str]:
        values = [v for v in params.getlist(key) if v is not None]
        if values:
            return values[-1]
        for fb in fallbacks:
            if fb is not None:
                return fb
        return None

    raw_action = _last_value("action", action, "redact")
    raw_mode = _last_value("param_mode", param_mode, initial_param_mode, "preset")
    preset_value = _last_value("param_preset", param_preset, initial_param_preset, DEFAULT_PRESET_KEY)
    free_value = _last_value("param_free", param_free, initial_param_free, "")
    pattern_value = _last_value("pattern", pattern, initial_pattern, "")
    repl_value = _last_value("repl", repl, initial_repl, "")

    act = _normalize_action(raw_action)
    mode = (raw_mode or "preset").strip().lower() or "preset"
    preset_selected = (preset_value or DEFAULT_PRESET_KEY).strip() or DEFAULT_PRESET_KEY
    free_text = (free_value or "").strip()
    pattern_text = (pattern_value or "").strip()
    repl_text = (repl_value or "").strip()

    if is_debug_enabled():
        try:
            log_debug_event(
                "deid:param_controls_resolved",
                act=act,
                mode=mode,
                preset=preset_selected,
                free=free_text,
                pattern=pattern_text,
                repl=repl_text,
            )
        except Exception:
            pass

    return templates.TemplateResponse(
        "ui/settings/_deid_param_controls.html",
        {
            "request": request,
            "action": act,
            "act": act,
            "param_mode": mode,
            "mode": mode,
            "param_preset": preset_selected,
            "param_free": free_text,
            "pattern": pattern_text,
            "repl": repl_text,
            "preset_options": PRESET_PARAM_OPTIONS,
        },
    )


@router.post("/ui/settings/deid/add_rule/{name}", response_class=HTMLResponse, name="ui_settings_deid_add_rule", response_model=None)
def ui_settings_deid_add_rule(
    request: Request,
    name: str,
    segment: str = Form(...),
    field: int = Form(...),
    component: Optional[str] = Form(None),
    subcomponent: Optional[str] = Form(None),
    action: str = Form("redact"),
    param_mode: Optional[str] = Form(None),
    param_preset: Optional[str] = Form(None),
    param_free: Optional[str] = Form(None),
    pattern: Optional[str] = Form(None),
    repl: Optional[str] = Form(None),
    initial_param_mode: Optional[str] = Form(None),
    initial_param_preset: Optional[str] = Form(None),
    initial_param_free: Optional[str] = Form(None),
    initial_pattern: Optional[str] = Form(None),
    initial_repl: Optional[str] = Form(None),
) -> Response:
    p = _json_path(DEID_DIR, name)
    tpl = DeidTemplate.from_dict(_load_json(p))
    tpl.rules = tpl.rules or []
    try:
        comp_val = None if component in (None, "") else int(component)
    except Exception:
        comp_val = None
    try:
        sub_val = None if subcomponent in (None, "") else int(subcomponent)
    except Exception:
        sub_val = None
    act = _normalize_action(action)
    mode = (param_mode or "preset").strip().lower() or "preset"
    if act == "preset":
        if mode == "preset":
            param_value = (param_preset or "").strip()
        else:
            param_value = (param_free or "").strip()
    elif act in {"replace", "mask", "hash"}:
        param_value = (param_free or "").strip()
    elif act == "regex_redact":
        param_value = (pattern or "").strip()
    elif act == "regex_replace":
        param_value = json.dumps({"pattern": (pattern or "").strip(), "repl": (repl or "").strip()})
    else:
        param_value = None

    new_rule = {
        "segment": segment.strip().upper(),
        "field": int(field),
        "component": comp_val,
        "subcomponent": sub_val,
        "action": act,
        "param": (param_value or None),
    }

    if _has_duplicate([asdict(r) for r in tpl.rules], new_rule):
        return templates.TemplateResponse(
            "ui/settings/_deid_rules_table.html",
            {"request": request, "tpl": tpl, "error": "Duplicate rule for the same path/action is not allowed."},
        )

    tpl.rules.append(DeidRule(**new_rule))
    _save_json(p, tpl.to_dict())
    return templates.TemplateResponse("ui/settings/_deid_rules_table.html", {"request": request, "tpl": tpl})


@router.post(
    "/api/tools/deid/test_rule",
    response_class=JSONResponse,
    name="api_deid_test_rule",
    response_model=None,
)
def api_deid_test_rule(
    message_text: str = Form(...),
    segment: str = Form(...),
    field: int = Form(...),
    component: Optional[str] = Form(None),
    subcomponent: Optional[str] = Form(None),
    action: str = Form(...),
    param_mode: Optional[str] = Form(None),
    param_preset: Optional[str] = Form(None),
    param_free: Optional[str] = Form(None),
    pattern: Optional[str] = Form(None),
    repl: Optional[str] = Form(None),
    initial_param_mode: Optional[str] = Form(None),
    initial_param_preset: Optional[str] = Form(None),
    initial_param_free: Optional[str] = Form(None),
    initial_pattern: Optional[str] = Form(None),
    initial_repl: Optional[str] = Form(None),
) -> JSONResponse:
    from silhouette_core.interop.deid import apply_single_rule

    c = int(component) if component and component.isdigit() else None
    s = int(subcomponent) if subcomponent and subcomponent.isdigit() else None
    act = _normalize_action(action)
    mode = (param_mode or "preset").strip().lower() or "preset"
    if act == "preset":
        param_value = (param_preset or "").strip() if mode == "preset" else (param_free or "").strip()
    elif act in {"replace", "mask", "hash"}:
        param_value = (param_free or "").strip()
    elif act == "regex_redact":
        param_value = (pattern or "").strip()
    elif act == "regex_replace":
        param_value = json.dumps({"pattern": (pattern or "").strip(), "repl": (repl or "").strip()})
    else:
        param_value = None
    rule = {
        "segment": segment.strip().upper(),
        "field": int(field),
        "component": c,
        "subcomponent": s,
        "action": act,
        "param": param_value,
    }
    try:
        preview = apply_single_rule(message_text or "", rule)
        return JSONResponse({"ok": True, "preview": preview})
    except Exception as e:  # pragma: no cover - defensive
        return JSONResponse({"ok": False, "error": f"{type(e).__name__}: {e}"}, status_code=200)

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


@router.get(
    "/ui/settings/deid/clone_rule_modal/{name}/{index}",
    response_class=HTMLResponse,
    name="ui_settings_deid_clone_rule_modal",
    response_model=None,
)
def ui_settings_deid_clone_rule_modal(request: Request, name: str, index: int) -> Response:
    p = _json_path(DEID_DIR, name)
    tpl = DeidTemplate.from_dict(_load_json(p))
    rules = tpl.rules or []
    if index < 0 or index >= len(rules):
        raise HTTPException(status_code=404, detail="Rule not found")
    clone_rule = rules[index]
    return templates.TemplateResponse(
        "ui/settings/_deid_rule_modal.html",
        _build_rule_modal_context(request, tpl, clone_rule),
    )


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
    return ui_settings_index(request)

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


@router.post(
    "/api/tools/validate/test_check",
    response_class=JSONResponse,
    name="api_validate_test_check",
    response_model=None,
)
def api_validate_test_check(
    message_text: str = Form(...),
    segment: str = Form(...),
    field: int = Form(...),
    required: bool = Form(False),
    pattern: Optional[str] = Form(None),
    allowed_values: Optional[str] = Form(None),
) -> JSONResponse:
    from silhouette_core.interop.validate_workbook import validate_with_template

    allowed = [v.strip() for v in (allowed_values or "").replace(";", ",").split(",") if v.strip()] or None
    required_flag = str(required).strip().lower() in {"1", "true", "yes", "on"}
    tpl = {
        "name": "_preview",
        "checks": [
            {
                "segment": segment.strip().upper(),
                "field": int(field),
                "required": required_flag,
                "pattern": pattern or None,
                "allowed_values": allowed,
            }
        ],
    }
    try:
        report = validate_with_template(message_text, tpl)
    except Exception as exc:  # pragma: no cover - defensive
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    return JSONResponse({"ok": True, "report": report})

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


@router.get(
    "/ui/settings/val/new_check_modal/{name}",
    response_class=HTMLResponse,
    name="ui_settings_val_new_check_modal",
    response_model=None,
)
def ui_settings_val_new_check_modal(request: Request, name: str) -> Response:
    tpl = ValidateTemplate.from_dict(_load_json(_json_path(VAL_DIR, name)))
    return templates.TemplateResponse("ui/settings/_val_check_modal.html", {"request": request, "tpl": tpl})

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
