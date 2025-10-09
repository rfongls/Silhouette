import asyncio
import importlib.util

import pytest
import yaml

from engine.contracts import Message
from engine.operators.deidentify import DeidentifyOperator
from engine.runtime import EngineRuntime
from engine.spec import load_pipeline_spec


if importlib.util.find_spec("silhouette_core") is None:
    pytest.skip("legacy validators/deid not installed", allow_module_level=True)


SAMPLE_MESSAGE = (
    "MSH|^~\\&|SENDER|FAC|REC|FAC|202501011200||ADT^A01|MSG0001|P|2.5\r"
    "PID|1||12345^^^HOSP^MR||DOE^JANE||19800101|F| | |123 MAIN ST^^TOWN^^12345^USA||^PRN^PH^^^5551234\r"
)

ACTIONS = {"PID-5.1": "remove", "PID-13": "mask"}


def _pipeline(operator_config: dict) -> dict:
    return {
        "version": 1,
        "name": "deidentify-phase1",
        "adapter": {
            "type": "sequence",
            "config": {
                "messages": [
                    {"id": "msg-1", "text": SAMPLE_MESSAGE},
                ]
            },
        },
        "operators": [
            {"type": "deidentify", "config": operator_config},
        ],
        "sinks": [
            {"type": "memory", "config": {"label": "deidentify-memory"}},
        ],
    }


def _run_pipeline(config: dict) -> list:
    spec_yaml = yaml.safe_dump(config, sort_keys=False)
    spec = load_pipeline_spec(spec_yaml)
    runtime = EngineRuntime(spec)
    return asyncio.run(runtime.run(max_messages=1))


def test_deidentify_inplace_modifies_payload():
    results = _run_pipeline(
        _pipeline({"actions": ACTIONS, "mode": "inplace"})
    )
    assert len(results) == 1
    updated = results[0].message.raw.decode("utf-8")
    assert "DOE" not in updated
    assert "JANE" in updated
    assert "5551234" not in updated
    meta = results[0].message.meta
    assert meta.get("deidentified") is True
    assert meta.get("deidentify_mode") == "inplace"
    assert any(issue.severity == "passed" and issue.code == "deidentify.applied" for issue in results[0].issues)


def test_deidentify_copy_mode_does_not_mutate_original_message():
    message = Message(id="msg-1", raw=SAMPLE_MESSAGE.encode("utf-8"), meta={})
    operator = DeidentifyOperator(name="deidentify", actions=ACTIONS, mode="copy")
    original_raw = message.raw
    result = asyncio.run(operator.process(message))
    assert message.raw == original_raw
    assert result.message.raw != original_raw
    assert result.message.meta.get("deidentify_mode") == "copy"
