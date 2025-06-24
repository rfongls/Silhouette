import argparse
import json
import zipfile
from pathlib import Path

from .quantize_models import quantize_embeddings


def load_profile(path: Path) -> dict:
    """Load a profile from JSON or ZIP."""
    if path.suffix == ".zip":
        with zipfile.ZipFile(path, "r") as zf:
            data = json.loads(zf.read("silhouette_profile.json").decode("utf-8"))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    return data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch Silhouette edge runtime")
    parser.add_argument("--profile", default="silhouette_profile.json")
    parser.add_argument("--distillate", default="distillate.json")
    args = parser.parse_args(argv)

    profile = load_profile(Path(args.profile))
    mem_entries = profile.get("memory", {}).get("entries", 0)
    print(f"Edge launcher loaded profile with {mem_entries} memory entries")

    dist_path = Path(args.distillate)
    if dist_path.exists():
        quantized = quantize_embeddings(dist_path, Path("embeddings.tflite"))
        print(f"Quantized embeddings ready at {quantized}")


if __name__ == "__main__":
    main()
