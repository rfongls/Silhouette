from __future__ import annotations
import json
from click.testing import CliRunner

# Be resilient to naming differences in the CLI entry
try:
    from silhouette_core.cli import main as silhouette_cli  # common case
except Exception:  # pragma: no cover
    try:
        from silhouette_core.cli import cli as silhouette_cli  # fallback alias
    except Exception as e:  # final fallback
        raise RuntimeError("Could not import Silhouette CLI group") from e


def test_cli_help_loads():
    r = CliRunner().invoke(silhouette_cli, ["--help"])
    assert r.exit_code == 0, r.output
    assert "Silhouette Core" in r.output


def test_summarize_ci_json_minimal_shape():
    # Summarize CI should work offline and print JSON when --json is passed.
    r = CliRunner().invoke(silhouette_cli, ["summarize", "ci", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert isinstance(data, dict)
    # We only check presence of top-level keys to keep the test stable across repos
    # At least one of these should show up depending on the repo
    assert any(k in data for k in ("ci_tools", "python", "node")), f"Unexpected shape: {list(data.keys())}"
