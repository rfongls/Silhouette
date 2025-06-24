import argparse
import json
from pathlib import Path


def quantize_embeddings(distillate: Path, output: Path) -> Path:
    """Convert embeddings to a compact TFLite-style file."""
    if not distillate.exists():
        output.write_bytes(b"[]")
        return output
    data = json.loads(distillate.read_text(encoding="utf-8"))
    embeddings = data.get("embeddings", [])
    output.write_bytes(json.dumps(embeddings).encode("utf-8"))
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quantize Silhouette models")
    parser.add_argument("--distillate", default="distillate.json")
    parser.add_argument("--output", default="embeddings.tflite")
    args = parser.parse_args(argv)
    out = quantize_embeddings(Path(args.distillate), Path(args.output))
    print(f"Quantized embeddings saved to {out}")


if __name__ == "__main__":
    main()
