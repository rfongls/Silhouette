import argparse
import json
from pathlib import Path


def load_config(path: Path) -> dict:
    cfg: dict[str, int] = {}
    if not path.is_file():
        return cfg
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = [x.strip() for x in line.split(":", 1)]
            try:
                cfg[key] = int(val)
            except ValueError:
                try:
                    cfg[key] = float(val)
                except ValueError:
                    cfg[key] = val
    return cfg


def summarize_memory(path: Path, limit: int = 10) -> dict:
    if not path.exists():
        return {"entries": 0, "core": []}
    core: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[:limit]:
        try:
            data = json.loads(line)
            core.append(data.get("content", ""))
        except json.JSONDecodeError:
            continue
    return {"entries": len(lines), "core": core}


def _vectorize(text: str) -> list[int]:
    return [len(text), sum(ord(c) for c in text)]


def _quantize(vec: list[int], bits: int) -> list[int]:
    max_val = max(vec) or 1
    scale = (2**bits) - 1
    return [int(v / max_val * scale) for v in vec]


def extract_embeddings(path: Path, limit: int = 10, bits: int = 8) -> list[list[int]]:
    if not path.exists():
        return []
    vectors = []
    for line in path.read_text(encoding="utf-8").splitlines()[:limit]:
        try:
            text = json.loads(line).get("content", "")
        except json.JSONDecodeError:
            text = ""
        vec = _vectorize(text)
        vectors.append(_quantize(vec, bits))
    return vectors


def distill(
    persona: Path = Path("persona.dsl"),
    memory: Path = Path("memory.jsonl"),
    config: Path = Path("config/distillation.yml"),
) -> dict:
    cfg = load_config(config)
    length = int(cfg.get("summary_length", 10))
    bits = int(cfg.get("quantization_bits", 8))
    summary = summarize_memory(memory, length)
    embeddings = extract_embeddings(memory, length, bits)
    persona_text = persona.read_text(encoding="utf-8") if persona.exists() else ""
    return {"persona": persona_text, "summary": summary, "embeddings": embeddings}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Distill Silhouette knowledge")
    parser.add_argument("--persona", default="persona.dsl")
    parser.add_argument("--memory", default="memory.jsonl")
    parser.add_argument("--config", default="config/distillation.yml")
    parser.add_argument("--output", type=Path, default=Path("distillate.json"))
    args = parser.parse_args(argv)

    data = distill(Path(args.persona), Path(args.memory), Path(args.config))
    args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Distillation saved to {args.output}")


if __name__ == "__main__":
    main()
