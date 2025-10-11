from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

from engine.spec import dump_pipeline_spec, load_pipeline_spec
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

    plan_assist = orchestrator.interpret(f"assist preview {pipeline.id} lookback 7")
    assert plan_assist.intent == "assist_preview"
    result_assist = asyncio.run(orchestrator.execute(store, plan_assist))
    assist_step = result_assist["report"][-1]
    assert assist_step["step"] == "assist_preview"
    assert "notes" in assist_step
    assert "draft_yaml" in assist_step

    job = store.enqueue_job(pipeline_id=pipeline.id, kind="run", payload={})
    plan_cancel = orchestrator.interpret(f"cancel job {job.id}")
    assert plan_cancel.intent == "cancel_job"
    result_cancel = asyncio.run(orchestrator.execute(store, plan_cancel))
    cancel_step = result_cancel["report"][-1]
    assert cancel_step["step"] == "cancel_job"
    assert cancel_step["status"] == "succeeded"
    canceled_job = store.get_job(job.id)
    assert canceled_job is not None and canceled_job.status == "canceled"


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
