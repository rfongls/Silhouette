import os
import pytest

from silhouette_core.hl7.versioning import (
    effective_versions,
    requested_versions_from_env,
)
from silhouette_core.hl7.utils import make_message, make_segment


VERSIONS = effective_versions(
    requested_versions_from_env(os.getenv("SILHOUETTE_HL7_VERSIONS"))
)


@pytest.mark.hl7
@pytest.mark.parametrize("version", VERSIONS)
def test_construct_and_parse_minimal(version: str) -> None:
    msg = make_message("ADT_A01", version)
    pid = make_segment("PID", version)
    msg.add(pid)
    assert msg.PID is not None
    assert msg.name.startswith("ADT_")

