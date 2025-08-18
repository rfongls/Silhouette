import json
import pathlib
import sys

REQUIRED = {"instruction", "input", "teacher_output"}

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
            for k in ["instruction", "input", "teacher_output"]:
                if not isinstance(obj[k], str):
                    raise SystemExit(f"Line {i}: field '{k}' must be a string")
            if "tools_used" in obj and not isinstance(obj["tools_used"], list):
                raise SystemExit(f"Line {i}: tools_used must be a list if present")
            n += 1
    print(f"OK: {n} teacher examples")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/validate_teacher_jsonl.py training_data/teacher_outputs.jsonl")
        sys.exit(2)
    main(sys.argv[1])
