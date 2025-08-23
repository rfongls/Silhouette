import os
import pathlib
import sys

import click

from . import __version__
from .repo_adapter import LocalRepoAdapter
from .repo_map import build_repo_map, save_repo_map
from .run_artifacts import record_run

DEFAULT_PROFILE = "profiles/core/policy.yaml"

def _echo(s):
    click.echo(s, err=False)

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
@click.option("--json-out", default="artifacts/repo_map.json", show_default=True)
@click.option("--compute-hashes", is_flag=True, help="Compute file hashes")
def repo_map_cmd(source, json_out, compute_hashes):
    """Create a repository map for ``source``."""
    adapter = LocalRepoAdapter(pathlib.Path(source))
    adapter.fetch(source)
    files = adapter.list_files(["**/*"])
    data = build_repo_map(adapter.root, files, compute_hashes=compute_hashes)
    out_path = pathlib.Path(json_out)
    with record_run(
        "repo_map",
        {"compute_hashes": compute_hashes, "json_out": str(out_path)},
        repo_root=adapter.root,
        policy_path=pathlib.Path("policy.yaml"),
    ):
        save_repo_map(data, out_path)
    _echo(f"Wrote {out_path}")

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


if __name__ == "__main__":
    main()
