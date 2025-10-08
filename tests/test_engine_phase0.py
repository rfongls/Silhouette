from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from insights.store import reset_store, seed as seed_insights


def _create_client(tmp_path, *, seed: bool = False, db_name: str = "insights.db"):
    db_path = tmp_path / db_name
    db_url = f"sqlite:///{db_path}"
    os.environ["ENGINE_V2"] = "1"
    os.environ["INSIGHTS_DB_URL"] = db_url
    reset_store()
    if seed:
        seed_insights(url=db_url)
    for module in ("server", "api.engine", "api.insights", "api.ui_engine"):
        sys.modules.pop(module, None)
    server = importlib.import_module("server")
    importlib.reload(server)
    client = TestClient(server.app)
    return client, db_url


def test_engine_health_endpoint(tmp_path):
    client, _ = _create_client(tmp_path)
    try:
        resp = client.get("/api/engine/health")
    finally:
        client.close()
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["feature"] == "engine-v2"


def test_pipeline_validate_example(tmp_path):
    client, _ = _create_client(tmp_path)
    try:
        payload = Path("examples/engine/minimal.pipeline.yaml").read_text(encoding="utf-8")
        resp = client.post("/api/engine/pipelines/validate", json={"yaml": payload})
    finally:
        client.close()
    assert resp.status_code == 200
    spec = resp.json()["spec"]
    assert spec["adapter"]["type"] == "sequence"
    assert spec["sinks"][0]["type"] == "memory"


def test_insights_summary_after_seed(tmp_path):
    client, _ = _create_client(tmp_path, seed=True, db_name="seeded.db")
    try:
        resp = client.get("/api/insights/summary")
    finally:
        client.close()
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["totals"]["runs"] >= 1
    assert summary["totals"]["messages"] >= 1
    assert any(item["count"] >= 1 for item in summary["by_rule"])


def test_engine_nav_visible(tmp_path):
    client, _ = _create_client(tmp_path, seed=True, db_name="nav.db")
    try:
        resp = client.get("/ui/engine")
    finally:
        client.close()
    assert resp.status_code == 200
    html = resp.text
    assert "Engine (Beta)" in html
    assert "/api/insights/summary" in html
