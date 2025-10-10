from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.engine import router as engine_router
from insights.store import InsightsStore, reset_store


def make_app_with_store(db_url: str):
    """Create a FastAPI app backed by a temporary Insights store."""
    app = FastAPI()
    app.include_router(engine_router)
    store = InsightsStore.from_env(url=db_url)
    store.ensure_schema()

    import api.engine as engine_module

    engine_module.get_store = lambda: store  # type: ignore[assignment]
    return app, store


def build_yaml(name: str = "demo") -> str:
    return f"""
version: 1
name: {name}
adapter:
  type: sequence
  config:
    messages:
      - id: \"m1\"
        text: hello
operators:
  - type: echo
sinks:
  - type: memory
"""


def test_pipeline_crud_and_run_endpoints(tmp_path):
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'api2b.db'}"
    app, _ = make_app_with_store(db_url)
    client = TestClient(app)
    yaml_body = build_yaml("demo")
    response = client.post("/api/engine/pipelines/validate", json={"yaml": yaml_body})
    assert response.status_code == 200, response.text
    assert response.json()["spec"]["name"] == "demo"

    response = client.post(
        "/api/engine/pipelines",
        json={"name": "demo", "yaml": yaml_body, "description": "phase2b"},
    )
    assert response.status_code == 200, response.text
    pipeline_id = response.json()["id"]
    assert isinstance(pipeline_id, int)

    response = client.get("/api/engine/pipelines")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "demo"

    response = client.get(f"/api/engine/pipelines/{pipeline_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "demo"
    assert "yaml" in data

    response = client.post(
        f"/api/engine/pipelines/{pipeline_id}/run",
        json={"persist": False, "max_messages": 2},
    )
    assert response.status_code == 200, response.text
    run_payload = response.json()
    assert run_payload["run_id"] is None
    assert run_payload["processed"] >= 1

    response = client.post(
        f"/api/engine/pipelines/{pipeline_id}/run",
        json={"persist": True, "max_messages": 2},
    )
    assert response.status_code == 200, response.text
    run_payload = response.json()
    assert isinstance(run_payload["run_id"], int)

    response = client.delete(f"/api/engine/pipelines/{pipeline_id}")
    assert response.status_code == 200

    response = client.delete(f"/api/engine/pipelines/{pipeline_id}")
    assert response.status_code == 404


def test_pipeline_name_conflict_and_limits(tmp_path):
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'api2b_limits.db'}"
    app, _ = make_app_with_store(db_url)
    client = TestClient(app)
    yaml_dup = build_yaml("dup")
    body = {"name": "dup", "yaml": yaml_dup}
    first = client.post("/api/engine/pipelines", json=body)
    assert first.status_code == 200
    dup = client.post("/api/engine/pipelines", json=body)
    assert dup.status_code == 409, dup.text

    oversize_yaml = "version: 1\nname: big\n" + ("#" * (200 * 1024 + 5))
    too_big = client.post("/api/engine/pipelines", json={"name": "big", "yaml": oversize_yaml})
    assert too_big.status_code == 413


def test_validate_unknown_component(tmp_path):
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'api2b_validate.db'}"
    app, _ = make_app_with_store(db_url)
    client = TestClient(app)

    bad_yaml = """
version: 1
name: bad
adapter:
  type: DOES_NOT_EXIST
operators: []
sinks: []
"""

    response = client.post("/api/engine/pipelines/validate", json={"yaml": bad_yaml})
    assert response.status_code == 400
    assert "Unknown" in response.text


def test_pipeline_name_mismatch_rejected(tmp_path):
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'api2b_mismatch.db'}"
    app, _ = make_app_with_store(db_url)
    client = TestClient(app)

    yaml_body = build_yaml("yaml-name")
    response = client.post(
        "/api/engine/pipelines",
        json={"name": "payload-name", "yaml": yaml_body},
    )
    assert response.status_code == 400
    assert "mismatch" in response.json().get("detail", "")


def test_pipeline_name_comparison_trims_whitespace(tmp_path):
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'api2b_trim.db'}"
    app, _ = make_app_with_store(db_url)
    client = TestClient(app)

    yaml_body = build_yaml("aligned-name")
    response = client.post(
        "/api/engine/pipelines",
        json={"name": "  aligned-name  ", "yaml": yaml_body},
    )
    assert response.status_code == 200, response.text


def test_issue_counts_normalizes_unknown_severity():
    from types import SimpleNamespace

    import api.engine as engine_module

    fake_results = [
        SimpleNamespace(
            issues=[
                SimpleNamespace(severity="error"),
                SimpleNamespace(severity="info"),
                SimpleNamespace(severity=None),
                SimpleNamespace(severity="passed"),
            ]
        )
    ]

    assert engine_module._issue_counts(fake_results) == {
        "error": 1,
        "warning": 2,
        "passed": 1,
    }
