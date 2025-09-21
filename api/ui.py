from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import NoMatchFound
from starlette.templating import Jinja2Templates

from api.debug_log import (
    is_debug_enabled,
    set_debug_enabled,
    tail_debug_lines,
    toggle_debug_enabled,
)
from skills.hl7_drafter import draft_message, send_message

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _link_for(request: Request, name: str, default_path: str, **path_params) -> str:
    """Best-effort url_for with fallback when the route isn't registered."""

    try:
        return request.url_for(name, **path_params)
    except NoMatchFound:
        root = request.scope.get("root_path", "")
        if default_path and not default_path.startswith("/"):
            default_path = "/" + default_path
        fallback = default_path or "/"
        return f"{root}{fallback}"


def install_link_for(env: Jinja2Templates) -> None:
    env.env.globals["link_for"] = _link_for


install_link_for(templates)
REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/api/ui/skills", response_class=JSONResponse, include_in_schema=False)
def api_skills_registry():
    """Expose enabled skills for navigation menus."""
    return JSONResponse(_load_skills())

@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/reports", response_class=HTMLResponse, name="ui_reports")
def ui_reports(request: Request):
    return templates.TemplateResponse("reports/index.html", {"request": request})


@router.get("/reports/acks", response_class=HTMLResponse, name="ui_reports_acks")
def ui_reports_acks(request: Request):
    return templates.TemplateResponse("reports/acks.html", {"request": request})


@router.get("/reports/validate", response_class=HTMLResponse, name="ui_reports_validate")
def ui_reports_validate(request: Request):
    return templates.TemplateResponse("reports/validate.html", {"request": request})

@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})

REG_PATH = Path("config/skills.yaml")


def _load_skills() -> list[dict]:
    """Load skills from registry, fallback to built-in defaults."""
    if REG_PATH.exists():
        data = yaml.safe_load(REG_PATH.read_text(encoding="utf-8")) or {}
        skills = data.get("skills") or []
    else:
        skills = [
            {
                "id": "interop",
                "name": "Interoperability",
                "desc": "Generate/de-ID/validate HL7, translate to FHIR, and transport via MLLP.",
                "dashboard": "/ui/interop/dashboard",
                "summary_url": "/interop/summary",
                "enabled": True,
            },
            {
                "id": "security",
                "name": "Security",
                "desc": "Run security tools, capture evidence, and review findings.",
                "dashboard": "/ui/security/dashboard",
                "summary_url": "/security/summary",
                "enabled": True,
            },
        ]
    norm = []
    for s in skills:
        if not s or not s.get("enabled"):
            continue
        norm.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "desc": s.get("desc", ""),
                "dashboard": s.get("dashboard", ""),
                "summary_url": s.get("summary_url", ""),
            }
        )
    return norm


@router.get("/", include_in_schema=False)
def root():
    # Default entry → Reports Home
    return RedirectResponse("/ui/home", status_code=307)


@router.get("/ui/home", response_class=HTMLResponse)
def ui_home(request: Request):
    """
    Reports Home — high-level KPIs and recent activity.
    Uses registry + HTMX to pull skill-specific summaries.
    """
    return templates.TemplateResponse("ui/home_reports.html", {"request": request, "skills": _load_skills()})


@router.get("/ui/skills", response_class=HTMLResponse)
def ui_skills_index(request: Request):
    """
    Skills Index — navigate to skill dashboards (Interop, Security, etc.).
    """
    return templates.TemplateResponse("ui/skills_index.html", {"request": request, "skills": _load_skills()})


def _sanitize_target_id(value: str | None) -> str:
    if not value:
        return "home-debug-log"
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in "-_:")
    return cleaned or "home-debug-log"


def _home_debug_context(
    request: Request, limit: int = 50, target_id: str | None = None
) -> dict:
    try:
        limit_int = int(limit)
    except (TypeError, ValueError):
        limit_int = 50
    limit_int = max(1, min(2000, limit_int))
    lines = tail_debug_lines(limit_int)
    recent_count = min(5, len(lines))
    recent = list(reversed(lines[-recent_count:])) if recent_count else []
    safe_target = _sanitize_target_id(target_id)
    return {
        "request": request,
        "enabled": is_debug_enabled(),
        "lines": lines,
        "recent": recent,
        "limit": limit_int,
        "total": len(lines),
        "refreshed": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "target_id": safe_target,
    }


@router.get("/ui/home/debug-log", response_class=HTMLResponse)
async def ui_home_debug_log(request: Request, limit: int = 50, target: str | None = None):
    ctx = _home_debug_context(request, limit, target)
    return templates.TemplateResponse("ui/_debug_alerts.html", ctx)


@router.post("/ui/home/debug-log", response_class=HTMLResponse)
async def ui_home_debug_log_update(request: Request):
    form = await request.form()
    action = (form.get("action") or "refresh").strip().lower()
    limit = form.get("limit") or form.get("tail") or form.get("count") or 50
    target = form.get("target")
    if action == "enable":
        set_debug_enabled(True)
    elif action == "disable":
        set_debug_enabled(False)
    elif action == "toggle":
        toggle_debug_enabled()
    ctx = _home_debug_context(request, limit, target)
    return templates.TemplateResponse("ui/_debug_alerts.html", ctx)


def _load_targets():
    p = Path("config/hosts.yaml")
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return data.get("targets", {})
    return {}

MESSAGE_TYPES = [
    "VXU^V04","RDE^O11","ORM^O01","OML^O21","ORU^R01:RAD","MDM^T02","ADT^A01","SIU^S12","DFT^P03"
]

def _render(request: Request, context: dict) -> HTMLResponse:
    ctx = dict(context)
    ctx.setdefault("request", request)
    return templates.TemplateResponse("ui/hl7_send.html", ctx)


@router.get("/ui/hl7", response_class=HTMLResponse)
async def get_form(request: Request):
    return _render(request, {"targets": _load_targets(), "message_types": MESSAGE_TYPES})

@router.post("/ui/hl7", response_class=HTMLResponse)
async def post_form(
    request: Request,
    message_type: str = Form(...),
    json_data: str = Form(""),
    host: str = Form(...),
    port: int = Form(...),
    action: str = Form("draft")
):
    result = {"message": "", "ack": ""}
    error = None
    try:
        payload = json.loads(json_data) if json_data.strip() else {}
        message = draft_message(message_type, payload)
        result["message"] = message
        if action == "draft_send":
            result["ack"] = await send_message(host, port, message)
    except Exception as e:
        error = str(e)

    return _render(
        request,
        {
            "targets": _load_targets(),
            "message_types": MESSAGE_TYPES,
            "selected_type": message_type,
            "selected_host": host,
            "selected_port": port,
            "json_data": json_data,
            "result": result,
            "error": error,
        },
    )
