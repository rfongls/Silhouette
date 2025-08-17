import json
import pathlib
import sys

REQUIRED = {"instruction", "input", "output"}

def main(path):
    p = pathlib.Path(path)
    assert p.exists(), f"File not found: {path}"
    n = 0
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                raise SystemExit(f"Line {i}: invalid JSON: {e}")
            missing = REQUIRED - obj.keys()
            if missing:
                raise SystemExit(f"Line {i}: missing keys {missing}")
            if not isinstance(obj["instruction"], str) or not isinstance(obj["input"], str) or not isinstance(obj["output"], str):
                raise SystemExit(f"Line {i}: fields must be strings (instruction/input/output)")
            if "tools_used" in obj and not isinstance(obj["tools_used"], list):
                raise SystemExit(f"Line {i}: tools_used must be a list if present")
            n += 1
    print(f"OK: {n} examples")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/validate_jsonl.py training_data/core.jsonl")
        sys.exit(2)
    main(sys.argv[1])
