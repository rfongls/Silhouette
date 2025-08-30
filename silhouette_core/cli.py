import json
import os
import pathlib
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from .analysis import hotpaths as analysis_hotpaths
from .analysis import service as analysis_service
from .analysis import suggest_tests as analysis_suggest_tests
from .analysis import summarize_ci as analysis_summarize_ci
from .impact.impact_set import compute_impact
from .patch.pr_body import compose_pr_body
from .patch.propose import propose_patch as propose_patch_fn
from .repo_adapter import LocalRepoAdapter
from .repo_map import build_repo_map, save_repo_map
from .run_artifacts import record_run

DEFAULT_PROFILE = "profiles/core/policy.yaml"

def _echo(s):
    click.echo(s, err=False)


def _load_graph(root: Path):
    try:
        from .graph.dep_graph import build_dep_graph
        return build_dep_graph(root)
    except Exception:
        graph: dict[str, set[str]] = {}
        for p in root.rglob("*.py"):
            graph[p.relative_to(root).as_posix()] = set()
        return graph

@click.group(context_settings={"help_option_names": ["-h","--help"]})
@click.version_option(__version__, prog_name="silhouette")
def main():
    """Silhouette Core — survivable, cross-language AI agent framework."""


@main.group("repo")
def repo_cmd():
    """Repository utilities."""
    pass


@repo_cmd.command("map")
@click.argument("source")
@click.option("--json-out", default="repo_map.json", show_default=True)
@click.option("--html-out", default="repo_map.html", show_default=True)
@click.option("--no-html", is_flag=True, help="Skip HTML rendering")
@click.option("--compute-hashes", is_flag=True, help="Compute file hashes")
def repo_map_cmd(source, json_out, html_out, no_html, compute_hashes):
    """Create a repository map for ``source``."""
    adapter = LocalRepoAdapter(pathlib.Path(source))
    adapter.fetch(source)
    files = adapter.list_files(["**/*"])
    with record_run(
        "repo_map",
        {
            "compute_hashes": compute_hashes,
            "json_out": Path(json_out).name,
            "html_out": None if no_html else Path(html_out).name,
        },
        repo_root=adapter.root,
        policy_path=pathlib.Path("policy.yaml"),
    ) as run_dir:
        data = build_repo_map(adapter.root, files, compute_hashes=compute_hashes)
        json_path = run_dir / Path(json_out).name
        save_repo_map(data, json_path)
        if not no_html:
            from .report.html_report import render_repo_map_html

            html_path = run_dir / Path(html_out).name
            render_repo_map_html(data, html_path)
    msg = f"Wrote {json_path}"
    if not no_html:
        msg += f" and {html_path}"
    _echo(msg)

@main.command("run")
@click.option("--profile", default=DEFAULT_PROFILE, show_default=True, help="Policy/profile YAML")
@click.option("--student-model", envvar="STUDENT_MODEL", default=None, help="Path to student model")
@click.option("--offline", is_flag=True, help="Force offline stub generation")
def run_cmd(profile, student_model, offline):
    """Start the interactive agent REPL."""
    os.environ["SILHOUETTE_PROFILE"] = profile
    if student_model:
        os.environ["STUDENT_MODEL"] = student_model
    if offline:
        os.environ["SILHOUETTE_OFFLINE"] = "1"
    from cli.main import main as repl
    sys.exit(repl())

@main.command("eval")
@click.option("--suite", required=True, help="Path to eval suite YAML")
@click.option("--require_runtime_env", is_flag=True, help="Fail if Docker/runtime not available")
def eval_cmd(suite, require_runtime_env):
    """Run the eval harness on a suite."""
    from eval.eval import main as eval_main
    sys.argv = ["eval", "--suite", suite] + (["--require_runtime_env"] if require_runtime_env else [])
    sys.exit(eval_main())

@main.command("build-runner")
@click.option("--suite", required=True)
@click.option("--require-runtime-env", is_flag=True)
def build_runner_cmd(suite, require_runtime_env):
    """Run containerized compile/test suites."""
    from eval.build_runner import main as br
    sys.argv = ["build_runner", "--suite", suite] + (["--require_runtime_env"] if require_runtime_env else [])
    sys.exit(br())

@main.command("synth-traces")
@click.option("--lane", multiple=True, help="Restrict to lanes (repeatable)")
def synth_traces_cmd(lane):
    """Convert runtime passes into KD traces."""
    from scripts.synthesize_traces import main as synth
    sys.argv = ["synthesize_traces"] + sum([["--lane", lane_name] for lane_name in lane], [])
    sys.exit(synth())

@main.command("train")
@click.option("--cfg", default="config/train.yaml", show_default=True)
@click.option("--mode", type=click.Choice(["sft","kd"]), default="sft", show_default=True)
def train_cmd(cfg, mode):
    """Train student via SFT or KD."""
    if mode == "sft":
        from training.train_sft import main as sft
        sys.argv = ["train_sft", "--cfg", cfg]
        sys.exit(sft())
    else:
        from training.train_kd import main as kd
        sys.argv = ["train_kd", "--cfg", cfg]
        sys.exit(kd())

@main.command("selfcheck")
@click.option("--policy", default=DEFAULT_PROFILE, show_default=True)
def selfcheck_cmd(policy):
    """Run policy & tool self-check."""
    from scripts.selfcheck import main as sc
    sys.argv = ["selfcheck", "--policy", policy]
    sys.exit(sc())

@main.command("package")
@click.option("--out", default="dist/", show_default=True)
def package_cmd(out):
    """Build wheel/sdist into dist/."""
    import subprocess
    pathlib.Path(out).mkdir(exist_ok=True, parents=True)
    subprocess.check_call([sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", out])
    _echo("Artifacts in " + out)

@main.command("quantize")
@click.option("--method", type=click.Choice(["int8","gguf","onnx-int8"]), required=True)
@click.option("--src", required=True)
@click.option("--out", required=True)
def quantize_cmd(method, src, out):
    """Quantize/export a student model for edge/CPU deployment."""
    from scripts.quantize import main as q
    sys.argv = ["quantize", "--method", method, "--src", src, "--out", out]
    sys.exit(q())

@main.command("latency")
def latency_cmd():
    """Run latency probe."""
    from scripts.latency_probe import main as lp
    sys.argv = ["latency_probe"]
    sys.exit(lp())

@main.command("license")
@click.option("--customer-id", required=True)
@click.option("--out", default="artifacts/licenses")
def license_cmd(customer_id, out):
    """Issue a customer license and embed ID into WATERMARK.json."""
    import sys

    from scripts.issue_customer_license import main as issue

    sys.argv = [
        "issue_customer_license",
        "--customer-id",
        customer_id,
        "--out",
        out,
    ]
    sys.exit(issue())


@main.group("fhir")
def fhir_group():
    """FHIR utilities."""
    pass


@fhir_group.command("translate")
@click.option("--in", "input_path", required=True, help="HL7 v2 file, dir, or glob")
@click.option("--rules", help="Validation profile YAML")
@click.option("--map", "map_path", help="Mapping profile YAML")
@click.option(
    "--bundle",
    type=click.Choice(["transaction", "collection"]),
    default="transaction",
    show_default=True,
)
@click.option("--out", default="out/", show_default=True, help="Output directory")
@click.option("--server", default=None, help="FHIR server base URL")
@click.option("--token", default=None, help="Auth token for FHIR server")
@click.option("--validate", is_flag=True, help="Validate output resources")
@click.option("--dry-run", is_flag=True, help="Run without posting to server")
@click.option("--message-mode", is_flag=True, help="Emit message bundles with MessageHeader")
@click.option("--partner", default=None, help="Partner config to apply")
@click.option("--message-endpoint", default=None, help="Endpoint for message bundle POST")
@click.option("--notify-url", default=None, help="Webhook to notify on translation")
@click.option("--deid", is_flag=True, help="Redact PHI such as names")

def fhir_translate_cmd(
    input_path,
    rules,
    map_path,
    bundle,
    out,
    server,
    token,
    validate,
    dry_run,
    message_mode,
    partner,
    message_endpoint,
    notify_url,
    deid,
):
    """Translate HL7 v2 messages to FHIR (stub)."""
    from .pipelines import hl7_to_fhir

    hl7_to_fhir.translate(
        input_path=input_path,
        rules=rules,
        map_path=map_path,
        bundle=bundle,
        out=out,
        server=server,
        token=token,
        validate=validate,
        dry_run=dry_run,
        message_mode=message_mode,
        partner=partner,
        message_endpoint=message_endpoint,
        notify_url=notify_url,
        deidentify=deid,
    )


@fhir_group.command("validate")
@click.option(
    "--in",
    "in_glob",
    required=False,
    type=str,
    help="Literal glob for NDJSON files, e.g. 'out/fhir/ndjson/*.ndjson' (quote on PowerShell)",
)
@click.option(
    "--in-dir",
    "in_dir",
    required=False,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing NDJSON files.",
)
@click.option("--hapi", is_flag=True, help="Also run HAPI FHIR validator")
@click.option("--partner", default=None, help="Partner config to apply")
@click.option(
    "--tx-cache", default=None, help="Directory with ValueSet JSON for offline terminology checks"
)
@click.option(
    "--server",
    default="http://localhost:8080/fhir",
    show_default=True,
    help="HAPI FHIR base URL (used with --hapi)",
)
def fhir_validate_cmd(in_glob, in_dir, hapi, partner, tx_cache, server):
    """Validate NDJSON FHIR resources."""
    import glob
    import json
    from validators.fhir_profile import (
        validate_structural_with_pydantic,
        validate_uscore_jsonschema,
    )

    paths: list[Path] = []
    if in_glob:
        paths = [Path(p) for p in glob.glob(in_glob)]
    elif in_dir:
        paths = sorted(Path(in_dir).glob("*.ndjson"))
    else:
        raise click.UsageError("Provide either --in <glob> or --in-dir <folder>.")

    if not paths:
        raise click.ClickException("No NDJSON files found for input.")

    click.echo(f"Preparing to validate {len(paths)} file(s).")

    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                res = json.loads(line)
                validate_uscore_jsonschema(res)
                validate_structural_with_pydantic(res)
                if tx_cache:
                    from validators.fhir_profile import validate_terminology

                    validate_terminology(res, tx_cache)

    if hapi:
        click.echo(f"Validating against HAPI server: {server}")
        from validators import hapi_cli

        package_ids = None
        if partner:
            p_cfg = yaml.safe_load(
                Path(f"config/partners/{partner}.yaml").read_text(encoding="utf-8")
            )
            package_ids = p_cfg.get("package_ids")
        hapi_cli.run([str(p) for p in paths], package_ids=package_ids)

    from skills import audit
    for p in paths:
        audit.emit_and_persist(
            audit.fhir_audit_event("validate", "success", "cli", str(p))
        )


@fhir_group.command("bulk-bundle")
@click.option("--in", "input_dir", required=True, help="Directory of NDJSON resources")
@click.option("--out", default="out/fhir/bulk", show_default=True, help="Output directory")
@click.option("--batch", default=100, show_default=True, help="Resources per batch file")
def fhir_bulk_bundle_cmd(input_dir, out, batch):
    """Bundle NDJSON resources into batches for bulk import."""
    from .pipelines import bulk

    bulk.bundle_ndjson(input_dir, out, batch)


@fhir_group.command("render-v2")
@click.option("--in", "input_path", required=True, help="FHIR bundle JSON")
@click.option("--map", "map_path", default=None, help="Reverse mapping YAML")
@click.option("--out", default="out/hl7", show_default=True, help="Output directory")
def fhir_render_v2_cmd(input_path, map_path, out):
    """Render FHIR bundles back to HL7 v2 messages (stub)."""
    from .pipelines import fhir_to_v2

    fhir_to_v2.render(input_path=input_path, map_path=map_path, out=out)


@main.group("hl7")
def hl7_group():
    """HL7 v2 utilities."""
    pass


@hl7_group.command("mllp-gateway")
@click.option("--listen", default="127.0.0.1:2575", show_default=True, help="Host:port to bind")
@click.option("--out", default="out/hl7", show_default=True, help="Directory to write messages")
def hl7_mllp_gateway_cmd(listen, out):
    """Run a minimal MLLP server that writes inbound messages."""
    from .pipelines import mllp_gateway

    host, port = listen.split(":")
    mllp_gateway.run(host=host, port=int(port), out_dir=out)


@fhir_group.command("render-v2")
@click.option("--in", "input_path", required=True, help="FHIR bundle JSON")
@click.option("--map", "map_path", default=None, help="Reverse mapping YAML")
@click.option("--out", default="out/hl7", show_default=True, help="Output directory")
def fhir_render_v2_cmd(input_path, map_path, out):
    """Render FHIR bundles back to HL7 v2 messages (stub)."""
    from .pipelines import fhir_to_v2

    fhir_to_v2.render(input_path=input_path, map_path=map_path, out=out)


@main.group("hl7")
def hl7_group():
    """HL7 v2 utilities."""
    pass


@hl7_group.command("mllp-gateway")
@click.option("--listen", default="127.0.0.1:2575", show_default=True, help="Host:port to bind")
@click.option("--out", default="out/hl7", show_default=True, help="Directory to write messages")
def hl7_mllp_gateway_cmd(listen, out):
    """Run a minimal MLLP server that writes inbound messages."""
    from .pipelines import mllp_gateway

    host, port = listen.split(":")
    mllp_gateway.run(host=host, port=int(port), out_dir=out)


@main.group("analyze")
def analyze_group():
    """Static analyses."""
    pass


@analyze_group.command("hotpaths")
@click.option("--json", "json_out", is_flag=True, help="Output JSON")
def analyze_hotpaths_cmd(json_out):
    root = Path(".")
    graph = _load_graph(root)
    data = analysis_hotpaths.analyze(graph)
    if json_out:
        click.echo(json.dumps(data))
    else:
        for n in data["nodes"]:
            _echo(f"{n['path']}: {n['centrality']:.2f}")


@analyze_group.command("service")
@click.argument("path")
@click.option("--json", "json_out", is_flag=True, help="Output JSON")
def analyze_service_cmd(path, json_out):
    root = Path(".")
    graph = _load_graph(root)
    data = analysis_service.analyze(path, graph, root)
    if json_out:
        click.echo(json.dumps(data))
    else:
        _echo(data["service"])


@main.group("suggest")
def suggest_group():
    """Suggestions."""
    pass


@suggest_group.command("tests")
@click.argument("path")
@click.option("--json", "json_out", is_flag=True, help="Output JSON")
def suggest_tests_cmd(path, json_out):
    data = analysis_suggest_tests.suggest(path)
    if json_out:
        click.echo(json.dumps(data))
    else:
        _echo(str(data))


@main.group("summarize")
def summarize_group():
    """Summaries."""
    pass


@summarize_group.command("ci")
@click.option("--json", "json_out", is_flag=True, help="Output JSON")
def summarize_ci_cmd(json_out):
    root = Path(".")
    data = analysis_summarize_ci.summarize(root)
    if json_out:
        click.echo(json.dumps(data))
    else:
        _echo(str(data))

@main.group("propose")
def propose_group():
    """Proposals."""
    pass


@propose_group.command("patch")
@click.option("--goal", required=True)
@click.option("--hint", multiple=True, help="File hints")
@click.option("--strategy", default="textual", show_default=True)
def propose_patch_cmd(goal, hint, strategy):
    hints = sorted(hint)
    with record_run(
        "propose_patch",
        {"goal": goal, "hints": hints, "strategy": strategy},
        repo_root=Path("."),
        policy_path=Path("policy.yaml"),
    ) as run_dir:
        result = propose_patch_fn(goal, hints=hints, strategy=strategy)
        if not result["summary"]["files_changed"]:
            raise click.ClickException("No permissible targets after policy filtering")
        diff_path = run_dir / "proposed_patch.diff"
        diff_path.write_text(result["diff"], encoding="utf-8")
        impact = compute_impact(result["summary"]["files_changed"])
        (run_dir / "impact_set.json").write_text(
            json.dumps(impact), encoding="utf-8"
        )
        pr_body = compose_pr_body(goal, impact, result["summary"])
        (run_dir / "proposed_pr_body.md").write_text(pr_body, encoding="utf-8")
    _echo(f"Wrote {diff_path}")

if __name__ == "__main__":
    main()
