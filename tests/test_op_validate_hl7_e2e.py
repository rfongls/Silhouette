import asyncio
import importlib.util

import pytest
import yaml

from engine.runtime import EngineRuntime
from engine.spec import load_pipeline_spec


if importlib.util.find_spec("silhouette_core") is None:
    pytest.skip("legacy validators/deid not installed", allow_module_level=True)


VALID_MESSAGE = (
    "MSH|^~\\&|SENDER|FAC|REC|FAC|202501011200||ADT^A01|MSG0001|P|2.5\r"
    "PID|1||12345^^^HOSP^MR||DOE^JOHN||19800101|M\r"
    "PV1|1|I|2000^2012^01\r"
)

MISSING_PV1_MESSAGE = (
    "MSH|^~\\&|SENDER|FAC|REC|FAC|202501011200||ADT^A01|MSG0001|P|2.5\r"
    "PID|1||12345^^^HOSP^MR||DOE^JOHN||19800101|M\r"
)


def _make_pipeline(message: str, operator_config: dict) -> dict:
    return {
        "version": 1,
        "name": "validate-phase1",
        "adapter": {
            "type": "sequence",
            "config": {
                "messages": [
                    {"id": "msg-1", "text": message},
                ]
            },
        },
        "operators": [
            {"type": "validate-hl7", "config": operator_config},
        ],
        "sinks": [
            {"type": "memory", "config": {"label": "validate-memory"}},
        ],
    }


def _run_pipeline(spec_dict: dict) -> list:
    spec_yaml = yaml.safe_dump(spec_dict, sort_keys=False)
    spec = load_pipeline_spec(spec_yaml)
    runtime = EngineRuntime(spec)
    return asyncio.run(runtime.run(max_messages=1))


def test_validate_hl7_emits_pass_issue_for_valid_message():
    results = _run_pipeline(
        _make_pipeline(
            VALID_MESSAGE,
            {"profile": "ADT_A01", "strict": False},
        )
    )
    assert len(results) == 1
    issues = results[0].issues
    assert any(issue.code == "validate.ok" and issue.severity == "passed" for issue in issues)


def test_validate_hl7_reports_missing_pv1_as_error_when_strict():
    results = _run_pipeline(
        _make_pipeline(
            MISSING_PV1_MESSAGE,
            {"profile": "ADT_A01", "strict": True},
        )
    )
    issue = next((item for item in results[0].issues if item.code == "validate.segment.missing"), None)
    assert issue is not None
    assert issue.severity == "error"
    assert issue.segment == "PV1"


def test_validate_hl7_missing_pv1_is_warning_when_not_strict():
    results = _run_pipeline(
        _make_pipeline(
            MISSING_PV1_MESSAGE,
            {"profile": "ADT_A01", "strict": False},
        )
    )
    issue = next((item for item in results[0].issues if item.code == "validate.segment.missing"), None)
    assert issue is not None
    assert issue.severity == "warning"
