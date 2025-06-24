import argparse
import zipfile
from pathlib import Path

CORE_FILES = [
    "silhouette_core/edge_launcher.py",
    "silhouette_core/response_engine.py",
    "silhouette_core/memory_core.py",
    "silhouette_core/module_loader.py",
    "silhouette_core/dsl_parser.py",
    "silhouette_core/offline_mode.py",
]


def package_clone(
    profile: Path,
    distillate: Path | None = None,
    version: int = 1,
    output_dir: Path = Path("."),
) -> Path:
    """Create a clone archive with core code, profile, and distillate."""
    out = output_dir / f"silhouette_clone_v{version}.zip"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in CORE_FILES:
            path = Path(file)
            if path.exists():
                zf.write(path, arcname=Path(file).name)
        zf.write(profile, arcname="silhouette_profile.json")
        if distillate and distillate.exists():
            zf.write(distillate, arcname="distillate.json")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Package a Silhouette clone")
    parser.add_argument("--profile", default="silhouette_profile.json")
    parser.add_argument("--distillate", default="distillate.json")
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args(argv)

    out = package_clone(
        Path(args.profile),
        Path(args.distillate) if args.distillate else None,
        args.version,
        Path(args.output_dir),
    )
    print(f"Clone archive created at {out}")


if __name__ == "__main__":
    main()
