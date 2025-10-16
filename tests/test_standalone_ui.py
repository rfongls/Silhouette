from __future__ import annotations

import importlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

import api.ui_standalone as ui_standalone

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def build_client(monkeypatch, flag_value: str | None) -> TestClient:
    if flag_value is None:
        monkeypatch.delenv("SILH_STANDALONE_ENABLE", raising=False)
    else:
        monkeypatch.setenv("SILH_STANDALONE_ENABLE", flag_value)
    module = importlib.reload(ui_standalone)
    app = FastAPI()
    module.install(app)
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    return TestClient(app)


def test_standalone_pipeline_enabled(monkeypatch):
    client = build_client(monkeypatch, "1")
    try:
        response = client.get("/ui/standalone/pipeline")
        assert response.status_code == 200
        assert "HL7 Test Bench" in response.text

        deid_opts = client.get("/ui/standalone/deid/templates")
        assert deid_opts.status_code == 200
        assert "<option" in deid_opts.text

        redirect = client.get("/ui/standalonepipeline", follow_redirects=False)
        assert redirect.status_code == 307
        assert redirect.headers["location"].endswith("/ui/standalone/pipeline")
    finally:
        client.close()


def test_standalone_pipeline_disabled(monkeypatch):
    client = build_client(monkeypatch, "0")
    try:
        response = client.get("/ui/standalone/pipeline")
        assert response.status_code == 404

        redirect = client.get("/ui/standalonepipeline", follow_redirects=False)
        assert redirect.status_code == 404
    finally:
        client.close()

    cleanup_client = build_client(monkeypatch, None)
    cleanup_client.close()
