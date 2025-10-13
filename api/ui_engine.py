"""Engine UI routes (feature-flagged behind ENGINE_V2)."""
from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterable

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import Select, create_engine, select
from sqlalchemy.orm import Session, sessionmaker, selectinload

from api.ui import install_link_for, templates as base_templates
from engine.models import Direction, Endpoint, EngineInterface, Protocol
from engine.runtime import EngineInterfaceRuntime

router = APIRouter()

templates = base_templates
install_link_for(templates)

_runtime = EngineInterfaceRuntime()
_SessionMaker: sessionmaker | None = None


@dataclass(slots=True)
class EndpointView:
    id: int
    protocol: str
    host: str | None = None
    port: int | None = None
    path: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class InterfaceView:
    id: int
    name: str
    direction: str
    description: str | None
    pipeline_id: str | None
    is_active: bool
    endpoints: list[EndpointView] = field(default_factory=list)

    @property
    def direction_label(self) -> str:
        return self.direction.capitalize()


def _get_sessionmaker() -> sessionmaker:
    global _SessionMaker
    if _SessionMaker is None:
        db_url = os.getenv("INSIGHTS_DB_URL", "sqlite:///data/insights.db")
        engine = create_engine(db_url, future=True)
        _SessionMaker = sessionmaker(engine, expire_on_commit=False)
    return _SessionMaker


@contextmanager
def _session_scope() -> Iterable[Session]:
    session = _get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _coerce_direction(value: str) -> Direction:
    try:
        normalized = value.strip().lower()
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail="Invalid direction") from exc

    try:
        return Direction(normalized)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail="Invalid direction") from exc


def _coerce_protocol(value: str) -> Protocol:
    try:
        normalized = value.strip().lower()
    except AttributeError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail="Invalid protocol") from exc

    try:
        return Protocol(normalized)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=400, detail="Invalid protocol") from exc


def _serialize_endpoint(ep: Endpoint) -> EndpointView:
    protocol = ep.protocol
    if isinstance(protocol, Protocol):
        protocol = protocol.value
    return EndpointView(
        id=ep.id,
        protocol=str(protocol).upper(),
        host=ep.host,
        port=ep.port,
        path=ep.path,
        notes=ep.notes,
    )


def _serialize_interface(entity: EngineInterface) -> InterfaceView:
    direction = entity.direction
    if isinstance(direction, Direction):
        direction = direction.value
    endpoints = [_serialize_endpoint(ep) for ep in entity.endpoints]
    return InterfaceView(
        id=entity.id,
        name=entity.name,
        direction=str(direction),
        description=entity.description,
        pipeline_id=entity.pipeline_id,
        is_active=bool(entity.is_active),
        endpoints=endpoints,
    )


def _interface_query() -> Select[tuple[EngineInterface]]:
    return select(EngineInterface).options(selectinload(EngineInterface.endpoints))


def _list_interfaces(db: Session) -> list[InterfaceView]:
    result = db.scalars(_interface_query().order_by(EngineInterface.id.desc()))
    return [_serialize_interface(rec) for rec in result]


def _get_interface(db: Session, interface_id: int) -> InterfaceView | None:
    record = db.execute(
        _interface_query().where(EngineInterface.id == interface_id)
    ).scalar_one_or_none()
    if record is None:
        return None
    return _serialize_interface(record)


@router.get("/ui/engine", response_class=HTMLResponse, name="ui_engine_index")
def ui_engine_index(request: Request) -> HTMLResponse:
    """Engine hub entry point."""

    return templates.TemplateResponse("ui/engine/index.html", {"request": request})


@router.get("/ui/engine/pipelines", response_class=HTMLResponse, name="ui_engine_pipelines")
def ui_engine_pipelines(request: Request) -> HTMLResponse:
    """Legacy pipeline builder."""

    return templates.TemplateResponse("ui/engine/pipelines.html", {"request": request})


@router.get("/ui/engine/interfaces", response_class=HTMLResponse)
def ui_engine_interfaces(request: Request) -> HTMLResponse:
    with _session_scope() as db:
        items = _list_interfaces(db)
    return templates.TemplateResponse("engine/interfaces.html", {"request": request, "items": items})


@router.post("/ui/engine/interfaces/create")
def create_interface(
    request: Request,
    name: str = Form(...),
    direction: str = Form(...),
    description: str | None = Form(None),
    pipeline_id: str | None = Form(None),
):
    cleaned_name = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="Name is required")

    direction_enum = _coerce_direction(direction)
    description_value = _normalize_optional(description)
    pipeline_value = _normalize_optional(pipeline_id)

    with _session_scope() as db:
        existing = db.scalar(select(EngineInterface).where(EngineInterface.name == cleaned_name))
        if existing is not None:
            items = _list_interfaces(db)
            return templates.TemplateResponse(
                "engine/partials/interface_list.html",
                {
                    "request": request,
                    "items": items,
                    "message": f"Interface '{cleaned_name}' already exists.",
                },
                status_code=400,
            )
        record = EngineInterface(
            name=cleaned_name,
            direction=direction_enum.value,
            description=description_value,
            pipeline_id=pipeline_value,
            is_active=False,
        )
        db.add(record)
        db.commit()
        items = _list_interfaces(db)

    message = f"Interface '{cleaned_name}' created."
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "engine/partials/interface_list.html",
            {"request": request, "items": items, "message": message},
        )
    return RedirectResponse("/ui/engine/interfaces", status_code=303)


@router.post("/ui/engine/interfaces/delete")
def delete_interface(request: Request, interface_id: int = Form(...)):
    with _session_scope() as db:
        record = db.get(EngineInterface, interface_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Interface not found")
        name = record.name
        db.delete(record)
        db.commit()
        items = _list_interfaces(db)

    message = f"Interface '{name}' deleted."
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "engine/partials/interface_list.html",
            {"request": request, "items": items, "message": message},
        )
    return RedirectResponse("/ui/engine/interfaces", status_code=303)


@router.post("/ui/engine/interfaces/toggle")
def toggle_interface(
    request: Request,
    interface_id: int = Form(...),
    action: str = Form(...),
):
    hx_target = request.headers.get("HX-Target", "")
    message = ""
    with _session_scope() as db:
        record = db.get(EngineInterface, interface_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Interface not found")
        if action == "start":
            _runtime.start_interface(db, interface_id)
            message = f"Interface '{record.name}' started."
        elif action == "stop":
            _runtime.stop_interface(db, interface_id)
            message = f"Interface '{record.name}' stopped."
        else:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=400, detail="Unknown action")
        interface_view = _get_interface(db, interface_id)
        items = _list_interfaces(db)

    if hx_target.replace("#", "") == "interface-status":
        return templates.TemplateResponse(
            "engine/partials/interface_status.html",
            {"request": request, "interface": interface_view, "message": message},
        )

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "engine/partials/interface_list.html",
            {"request": request, "items": items, "message": message},
        )
    return RedirectResponse("/ui/engine/interfaces", status_code=303)


@router.post("/ui/engine/interfaces/test")
def test_interface(request: Request, interface_id: int = Form(...)):
    hx_target = request.headers.get("HX-Target", "")
    with _session_scope() as db:
        record = db.get(EngineInterface, interface_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Interface not found")
        result = _runtime.test_interface(db, interface_id)
        interface_view = _get_interface(db, interface_id)

    message = result.get("message") or "Test completed."
    payload = {
        "request": request,
        "interface": interface_view,
        "message": message,
        "test_result": result,
    }
    if hx_target.replace("#", "") == "interface-status" or request.headers.get("HX-Request"):
        return templates.TemplateResponse("engine/partials/interface_status.html", payload)
    return JSONResponse(result)


@router.post("/ui/engine/endpoints/add")
def add_endpoint(
    request: Request,
    interface_id: int = Form(...),
    protocol: str = Form(...),
    host: str | None = Form(None),
    port: str | None = Form(None),
    path: str | None = Form(None),
    notes: str | None = Form(None),
):
    port_value: int | None = None
    if port is not None and str(port).strip():
        try:
            port_value = int(str(port).strip())
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=400, detail="Port must be an integer") from exc

    protocol_enum = _coerce_protocol(protocol)

    with _session_scope() as db:
        interface = db.get(EngineInterface, interface_id)
        if interface is None:
            raise HTTPException(status_code=404, detail="Interface not found")
        endpoint = Endpoint(
            interface_id=interface_id,
            protocol=protocol_enum.value,
            host=_normalize_optional(host),
            port=port_value,
            path=_normalize_optional(path),
            notes=_normalize_optional(notes),
        )
        db.add(endpoint)
        db.commit()
        interface_view = _get_interface(db, interface_id)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "engine/partials/endpoint_list.html",
            {"request": request, "interface": interface_view},
        )
    return RedirectResponse(f"/ui/engine/interfaces/view/{interface_id}", status_code=303)


@router.get("/ui/engine/interfaces/view/{interface_id}", response_class=HTMLResponse)
def view_interface(request: Request, interface_id: int) -> HTMLResponse:
    with _session_scope() as db:
        interface_view = _get_interface(db, interface_id)
    if interface_view is None:
        raise HTTPException(status_code=404, detail="Interface not found")
    return templates.TemplateResponse(
        "engine/interface_detail.html",
        {"request": request, "interface": interface_view},
    )
