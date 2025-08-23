import pytest

import silhouette_core.compat.forwardref_shim  # noqa: F401


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "hl7: tests requiring hl7apy dictionaries and version support"
    )
