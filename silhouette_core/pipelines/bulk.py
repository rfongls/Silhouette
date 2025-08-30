from pathlib import Path
from typing import Iterable


def bundle_ndjson(input_dir: str, out_dir: str, batch_size: int = 100) -> None:
    """Bundle NDJSON resources from a directory into batched files."""
    src = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    batch = []
    idx = 0
    for path in sorted(src.glob("*.ndjson")):
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                batch.append(line)
                if len(batch) >= batch_size:
                    _write_batch(batch, out, idx)
                    idx += 1
                    batch = []
    if batch:
        _write_batch(batch, out, idx)


def _write_batch(lines: Iterable[str], out: Path, idx: int) -> None:
    target = out / f"batch_{idx:04d}.ndjson"
    with target.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
