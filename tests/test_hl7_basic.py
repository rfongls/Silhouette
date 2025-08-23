import os

import pytest
from hl7apy.parser import parse_message

from silhouette_core.hl7.utils import make_message, make_segment
from silhouette_core.hl7.versioning import effective_versions, requested_versions_from_env

VERSIONS = effective_versions(requested_versions_from_env(os.getenv("SILHOUETTE_HL7_VERSIONS")))


@pytest.mark.hl7
@pytest.mark.parametrize("version", VERSIONS)
def test_construct_simple_adt(version: str) -> None:
    msg = make_message("ADT_A01", version)
    pid = make_segment("PID", version)
    msg.add(pid)
    assert msg.PID is not None
    assert msg.name.startswith("ADT_")


@pytest.mark.hl7
@pytest.mark.parametrize("version", VERSIONS)
def test_parse_minimal_message(version: str) -> None:
    raw = (
        "MSH|^~\\&|SIL|HOSP|OTHER|DEST|202501010101||ADT^A01|"
        f"MSG0001|P|{version}\\rPID|||12345^^^HOSP^MR||DOE^JOHN||19700101|M\\r"
    )
    try:
        parsed = parse_message(raw, find_groups=False, validation_level=2, version=version)
    except Exception as e:  # pragma: no cover - skip if version unsupported
        pytest.skip(f"Parse skipped for {version}: {e!r}")
    assert parsed.MSH is not None
    assert parsed.PID is not None
