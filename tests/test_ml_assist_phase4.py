from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engine.contracts import Issue, Message, Result
from engine.ml_assist import compute_anomalies, render_draft_yaml, suggest_allowlist
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from insights.models import RunRecord
from insights.store import get_store, reset_store
from api.engine_assist import router as assist_router

PIPE = """
version: 1
name: ml-assist-pipe
adapter:
  type: sequence
  config:
    messages:
      - id: "m1"
        text: hello
operators:
  - type: echo
sinks:
  - type: memory
"""


def _seed(store):
    store.ensure_schema()
    spec = load_pipeline_spec(PIPE)
    pipeline = store.save_pipeline(
        name="ml-assist-pipe",
        yaml=PIPE,
        spec=dump_pipeline_spec(spec),
    )

    # Baseline run roughly 10 days ago with low volume.
    baseline_run = store.start_run(pipeline.name)
    store.record_result(
        run_id=baseline_run.id,
        result=Result(
            message=Message(id="baseline", raw=b"baseline"),
            issues=[Issue(severity="warning", code="validate.segment.missing", segment="PV1")],
        ),
    )
    with store.session() as session:
        record = session.get(RunRecord, baseline_run.id)
        record.created_at = datetime.utcnow() - timedelta(days=10)
        session.add(record)

    # Recent run with higher frequency of the same issue.
    recent_run = store.start_run(pipeline.name)
    for idx in range(3):
        store.record_result(
            run_id=recent_run.id,
            result=Result(
                message=Message(id=f"recent-{idx}", raw=b"recent"),
                issues=[Issue(severity="warning", code="validate.segment.missing", segment="PV1")],
            ),
        )

    return pipeline.id


def test_assist_suggestions_and_anomalies(tmp_path, monkeypatch):
    reset_store()
    monkeypatch.setenv("INSIGHTS_DB_URL", f"sqlite:///{tmp_path / 'assist4.db'}")
    store = get_store()
    pipeline_id = _seed(store)

    suggestions = suggest_allowlist(store, pipeline_id, now=datetime.utcnow())
    draft = render_draft_yaml(suggestions)
    assert draft.startswith("# --- BEGIN ML ASSIST")
    assert suggestions.allowlist

    anomalies = compute_anomalies(store, pipeline_id, now=datetime.utcnow())
    assert isinstance(anomalies, list)

    # API sanity check
    app = FastAPI()
    app.include_router(assist_router)
    client = TestClient(app)

    response = client.post(
        "/api/engine/assist/preview",
        json={"pipeline_id": pipeline_id, "lookback_days": 14},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["allowlist"]

    response = client.get(
        f"/api/engine/assist/anomalies?pipeline_id={pipeline_id}&recent_days=7&baseline_days=30",
    )
    assert response.status_code == 200, response.text
    assert isinstance(response.json()["items"], list)
