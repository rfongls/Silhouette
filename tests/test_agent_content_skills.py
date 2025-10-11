from __future__ import annotations

import asyncio
import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from engine.contracts import Issue, Message, Result
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from insights.models import AgentActionRecord, RunRecord
from insights.store import get_store, reset_store

PIPELINE_YAML = """
version: 1
name: deid-pipe
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


def _reload_orchestrator():
    for module_name in ["agent.orchestrator", "agent.fs_utils"]:
        if module_name in sys.modules:
            del sys.modules[module_name]
    orchestrator = importlib.import_module("agent.orchestrator")
    return orchestrator


def test_generate_and_deidentify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_DATA_ROOT", str(tmp_path / "agent"))

    reset_store()
    store = get_store()
    store.ensure_schema()

    orchestrator = _reload_orchestrator()
    fs_utils = importlib.import_module("agent.fs_utils")

    spec = load_pipeline_spec(PIPELINE_YAML)
    pipeline = store.save_pipeline(
        name="deid-pipe",
        yaml=PIPELINE_YAML,
        spec=dump_pipeline_spec(spec),
    )

    plan_generate = orchestrator.interpret("generate 3 ADT messages to demo-adt")
    result_generate = asyncio.run(orchestrator.execute(store, plan_generate))
    out_dir = fs_utils.out_folder("demo-adt")
    generated_files = sorted(out_dir.glob("*.hl7"))
    assert len(generated_files) == 3
    assert result_generate["report"][-1]["written"] == 3

    src_dir = fs_utils.in_folder("incoming/testward")
    (src_dir / "a.hl7").write_bytes(b"MSH|^~\\&|SIL|SRC|LAB|HOSP|202501010101||ADT^A01|X|P|2.5\rPID|1||A^B\r")
    (src_dir / "b.hl7").write_bytes(b"MSH|^~\\&|SIL|SRC|LAB|HOSP|202501010102||ADT^A08|Y|P|2.5\rPID|1||C^D\r")

    plan_deid = orchestrator.interpret(
        f"deidentify incoming/testward to testward_deid with pipeline {pipeline.id}"
    )
    result_deid = asyncio.run(orchestrator.execute(store, plan_deid))
    dst_dir = fs_utils.out_folder("testward_deid")
    output_files = sorted(dst_dir.glob("*.hl7"))
    assert len(output_files) == 2
    last_step = result_deid["report"][-1]
    assert last_step["ok"] == 2
    assert last_step["failed"] == 0
    assert last_step["failures"] == []

    with store.session() as session:
        action = session.query(AgentActionRecord).order_by(AgentActionRecord.id.desc()).first()
        assert action is not None
        summary = action.result.get("summary") if action.result else None
        assert summary is not None
        assert summary.get("ok") == 2
        assert summary.get("failed") == 0
        assert isinstance(summary.get("failures"), list)

    plan_assist = orchestrator.interpret(f"assist preview {pipeline.id} lookback 7")
    assert plan_assist.intent == "assist_preview"
    result_assist = asyncio.run(orchestrator.execute(store, plan_assist))
    assist_step = result_assist["report"][-1]
    assert assist_step["step"] == "assist_preview"
    assert "notes" in assist_step
    assert "draft_yaml" in assist_step

    with store.session() as session:
        action = session.query(AgentActionRecord).order_by(AgentActionRecord.id.desc()).first()
        assert action is not None
        summary = action.result.get("summary") if action.result else None
        assert summary is not None
        assert "assist_notes" in summary
        assert "allowlist_count" in summary
        assert "severity_rules_count" in summary

    job = store.enqueue_job(pipeline_id=pipeline.id, kind="run", payload={})
    plan_cancel = orchestrator.interpret(f"cancel job {job.id}")
    assert plan_cancel.intent == "cancel_job"
    result_cancel = asyncio.run(orchestrator.execute(store, plan_cancel))
    cancel_step = result_cancel["report"][-1]
    assert cancel_step["step"] == "cancel_job"
    assert cancel_step["status"] == "succeeded"
    canceled_job = store.get_job(job.id)
    assert canceled_job is not None and canceled_job.status == "canceled"

    with store.session() as session:
        action = session.query(AgentActionRecord).order_by(AgentActionRecord.id.desc()).first()
        assert action is not None
        summary = action.result.get("summary") if action.result else None
        assert summary is not None
        assert summary.get("canceled_job") == job.id


def test_assist_anomalies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_DATA_ROOT", str(tmp_path / "agent"))

    reset_store()
    store = get_store()
    store.ensure_schema()

    orchestrator = _reload_orchestrator()

    spec = load_pipeline_spec(PIPELINE_YAML)
    pipeline = store.save_pipeline(
        name="anomaly-pipe",
        yaml=PIPELINE_YAML,
        spec=dump_pipeline_spec(spec),
    )

    now = datetime.utcnow()

    baseline_run = store.start_run(pipeline.name)
    store.record_result(
        run_id=baseline_run.id,
        result=Result(
            message=Message(id="baseline", raw=b"BASE"),
            issues=[Issue(severity="warning", code="demo.code", segment="PV1")],
        ),
    )
    with store.session() as session:
        rec = session.get(RunRecord, baseline_run.id)
        assert rec is not None
        rec.created_at = now - timedelta(days=20)
        session.add(rec)

    recent_run = store.start_run(pipeline.name)
    for idx in range(4):
        store.record_result(
            run_id=recent_run.id,
            result=Result(
                message=Message(id=f"recent-{idx}", raw=b"RECENT"),
                issues=[Issue(severity="warning", code="demo.code", segment="PV1")],
            ),
        )

    plan = orchestrator.interpret(f"assist anomalies {pipeline.id} recent 7 baseline 30 minrate 0.01")
    assert plan.intent == "assist_anomalies"

    result = asyncio.run(orchestrator.execute(store, plan))
    step = result["report"][-1]
    assert step["step"] == "assist_anomalies"
    assert step["status"] == "succeeded"
    assert step["items"]
    assert any(item["code"] == "demo.code" for item in step["items"])

    with store.session() as session:
        action = session.query(AgentActionRecord).order_by(AgentActionRecord.id.desc()).first()
        assert action is not None
        summary = action.result.get("summary") if action.result else None
        assert summary is not None
        assert summary.get("anomalies") == len(step["items"])
        assert summary.get("recent_days") == 7
        assert summary.get("baseline_days") == 30
        assert "top_deviation" in summary
        assert summary.get("min_rate") == pytest.approx(0.01, rel=0, abs=1e-6)


def test_wildcard_bind_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENGINE_NET_BIND_ANY", raising=False)
    monkeypatch.setenv("AGENT_DATA_ROOT", str(tmp_path / "agent"))

    reset_store()
    store = get_store()
    store.ensure_schema()

    orchestrator = _reload_orchestrator()

    spec = load_pipeline_spec(PIPELINE_YAML)
    pipeline = store.save_pipeline(
        name="guard-pipe",
        yaml=PIPELINE_YAML,
        spec=dump_pipeline_spec(spec),
    )

    plan = orchestrator.interpret(
        f"create inbound guard-test on 0.0.0.0:4321 for pipeline {pipeline.id}"
    )
    result = asyncio.run(orchestrator.execute(store, plan))
    step = result["report"][-1]
    assert step["status"] == "failed"
    assert "blocked by policy" in step.get("error", "")
    assert store.get_endpoint_by_name("guard-test") is None
