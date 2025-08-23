import argparse
import json
import zipfile
from datetime import datetime
from pathlib import Path


def summarize_memory(path: Path, limit: int = 100) -> dict:
    if not path.exists():
        return {"entries": 0}
    lines = path.read_text(encoding="utf-8").splitlines()
    return {"entries": len(lines), "preview": lines[:limit]}


def list_modules(mod_dir: Path) -> list[dict]:
    modules = []
    if not mod_dir.exists():
        return modules
    for file in mod_dir.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            modules.append({
                "name": data.get("name", file.stem),
                "version": data.get("version", "unknown"),
            })
        except Exception:
            modules.append({"name": file.stem, "version": "error"})
    return modules


def collect_profile(
    persona: Path = Path("persona.dsl"),
    memory: Path = Path("memory.jsonl"),
    modules: Path = Path("modules"),
    manifest: Path = Path("PROJECT_MANIFEST.json"),
) -> dict:
    profile = {}
    profile["persona"] = persona.read_text(encoding="utf-8") if persona.exists() else ""
    profile["memory"] = summarize_memory(memory)
    profile["modules"] = list_modules(modules)
    if manifest.exists():
        try:
            profile["manifest"] = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            profile["manifest"] = {}
    else:
        profile["manifest"] = {}
    return profile


def export_profile(out: Path, as_zip: bool = False) -> Path:
    profile = collect_profile()
    data = json.dumps(profile, indent=2)
    if as_zip:
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("silhouette_profile.json", data)
    else:
        out.write_text(data, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export Silhouette profile")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--zip", action="store_true", help="Export as zip archive")
    args = parser.parse_args(argv)

    if args.output is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        args.output = Path(f"silhouette_profile_{ts}{'.zip' if args.zip else '.json'}")

    out_path = export_profile(args.output, as_zip=args.zip)
    print(f"Profile exported to {out_path}")


if __name__ == "__main__":
    main()
