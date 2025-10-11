from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.engine_jobs import router as engine_jobs_router
from engine.runner import EngineRunner
from engine.runtime import EngineRuntime
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from insights.models import MessageRecord
from insights.store import get_store, reset_store


PIPELINE_YAML = """
version: 1
name: seed-pipe
adapter:
  type: sequence
  config:
    messages:
      - id: "r1"
        text: hello
      - id: "r2"
        text: world
operators:
  - type: echo
sinks:
  - type: memory
"""


def test_replay_adapter_roundtrip(tmp_path, monkeypatch):
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'replay_roundtrip.db'}"
    monkeypatch.setenv("INSIGHTS_DB_URL", db_url)
    store = get_store()
    store.ensure_schema()

    spec = load_pipeline_spec(PIPELINE_YAML)
    pipeline = store.save_pipeline(
        name="replay-target",
        yaml=PIPELINE_YAML,
        spec=dump_pipeline_spec(spec),
    )

    runtime = EngineRuntime(spec)
    original_results = asyncio.run(runtime.run(max_messages=None))
    assert len(original_results) == 2
    original_run_id = store.persist_run_results(
        pipeline_name="seed-pipe",
        results=original_results,
    )

    app = FastAPI()
    app.include_router(engine_jobs_router)

    import api.engine_jobs as engine_jobs_module

    monkeypatch.setattr(engine_jobs_module, "get_store", lambda: store, raising=False)

    client = TestClient(app)
    response = client.post(
        "/api/engine/jobs",
        json={
            "pipeline_id": pipeline.id,
            "kind": "replay",
            "payload": {"replay_run_id": original_run_id},
        },
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]

    runner = EngineRunner(store=store, concurrency=1)
    now = datetime.utcnow()
    leased = store.lease_jobs(
        worker_id=runner.worker_id,
        now=now,
        lease_ttl_secs=30,
        limit=1,
    )
    assert leased and leased[0].id == job_id

    async def _execute():
        sem = asyncio.Semaphore(1)
        await sem.acquire()
        await runner._execute_job(leased[0], sem)

    asyncio.run(_execute())

    completed = store.get_job(job_id)
    assert completed is not None
    assert completed.status == "succeeded"
    assert completed.run_id is not None

    with store.session() as session:
        original_messages = (
            session.execute(
                select(MessageRecord)
                .where(MessageRecord.run_id == original_run_id)
                .order_by(MessageRecord.id.asc())
            )
            .scalars()
            .all()
        )
        replay_messages = (
            session.execute(
                select(MessageRecord)
                .where(MessageRecord.run_id == completed.run_id)
                .order_by(MessageRecord.id.asc())
            )
            .scalars()
            .all()
        )

    assert len(replay_messages) == len(original_messages)
    assert [msg.message_id for msg in replay_messages] == [msg.message_id for msg in original_messages]
    assert all(msg.meta.get("replay") for msg in replay_messages)
    assert all(msg.meta.get("source_run_id") == original_run_id for msg in replay_messages)
