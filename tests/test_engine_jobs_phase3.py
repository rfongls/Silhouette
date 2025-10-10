from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.engine import router as engine_router
from api.engine_jobs import router as engine_jobs_router
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from engine.runner import EngineRunner
from insights.store import InsightsStore, reset_store


def _make_store(tmp_path) -> tuple[InsightsStore, int]:
    reset_store()
    db_url = f"sqlite:///{tmp_path / 'jobs_phase3.db'}"
    store = InsightsStore.from_env(url=db_url)
    store.ensure_schema()
    yaml_body = _pipeline_yaml("job-pipeline")
    spec = dump_pipeline_spec(load_pipeline_spec(yaml_body))
    record = store.save_pipeline(name="job-pipeline", yaml=yaml_body, spec=spec)
    return store, record.id


def _pipeline_yaml(name: str) -> str:
    return f"""
version: 1
name: {name}
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


def _make_app(store: InsightsStore) -> FastAPI:
    app = FastAPI()
    app.include_router(engine_router)
    app.include_router(engine_jobs_router)

    import api.engine as engine_module
    import api.engine_jobs as engine_jobs_module

    engine_module.get_store = lambda: store  # type: ignore[assignment]
    engine_jobs_module.get_store = lambda: store  # type: ignore[assignment]
    return app


def test_enqueue_lease_complete_job(tmp_path):
    store, pipeline_id = _make_store(tmp_path)
    job = store.enqueue_job(pipeline_id=pipeline_id, payload={"persist": False})

    assert job.status == "queued"

    now = datetime.utcnow()
    leased = store.lease_jobs(
        worker_id="worker-1",
        now=now,
        lease_ttl_secs=30,
        limit=1,
    )
    assert len(leased) == 1
    assert leased[0].id == job.id

    running = store.start_job(job.id, "worker-1", now=now)
    assert running is not None
    assert running.status == "running"

    store.complete_job(job.id, run_id=None)
    finished = store.get_job(job.id)
    assert finished is not None
    assert finished.status == "succeeded"
    assert finished.leased_by is None


def test_fail_job_retries_until_dead(tmp_path):
    store, pipeline_id = _make_store(tmp_path)
    job = store.enqueue_job(pipeline_id=pipeline_id, max_attempts=2)

    now = datetime.utcnow()
    store.lease_jobs(worker_id="retry-worker", now=now, lease_ttl_secs=30, limit=1)
    store.fail_job_and_maybe_retry(
        job_id=job.id,
        error="boom",
        now=now,
        backoff_secs=5,
    )
    retried = store.get_job(job.id)
    assert retried is not None
    assert retried.status == "queued"
    assert retried.attempts == 1
    assert retried.scheduled_at >= now + timedelta(seconds=5)

    store.lease_jobs(worker_id="retry-worker", now=now + timedelta(seconds=10), lease_ttl_secs=30, limit=1)
    store.fail_job_and_maybe_retry(
        job_id=job.id,
        error="boom again",
        now=now,
        backoff_secs=5,
    )
    dead = store.get_job(job.id)
    assert dead is not None
    assert dead.status == "dead"
    assert dead.attempts == 2


def test_engine_runner_executes_job(tmp_path):
    store, pipeline_id = _make_store(tmp_path)
    job = store.enqueue_job(pipeline_id=pipeline_id, payload={"persist": False})
    runner = EngineRunner(store=store, concurrency=1)

    async def _run() -> None:
        now = datetime.utcnow()
        leased = store.lease_jobs(
            worker_id=runner.worker_id,
            now=now,
            lease_ttl_secs=30,
            limit=1,
        )
        assert leased
        sem = asyncio.Semaphore(1)
        await sem.acquire()
        await runner._execute_job(leased[0], sem)

    asyncio.run(_run())

    completed = store.get_job(job.id)
    assert completed is not None
    assert completed.status == "succeeded"


def test_job_api_endpoints(tmp_path):
    store, pipeline_id = _make_store(tmp_path)
    app = _make_app(store)
    client = TestClient(app)

    body = {
        "pipeline_id": pipeline_id,
        "kind": "run",
        "dedupe_key": "job-1",
        "payload": {"persist": False},
    }
    first = client.post("/api/engine/jobs", json=body)
    assert first.status_code == 200, first.text
    job_id = first.json()["id"]

    dup = client.post("/api/engine/jobs", json=body)
    assert dup.status_code == 409

    listed = client.get("/api/engine/jobs")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == job_id

    cancel = client.post(f"/api/engine/jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["canceled"] is True

    detail = client.get(f"/api/engine/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "canceled"

    retry = client.post(f"/api/engine/jobs/{job_id}/retry")
    assert retry.status_code == 200
    assert retry.json()["enqueued"] is True

    refreshed = client.get(f"/api/engine/jobs/{job_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "queued"
