import argparse
import json
import os
import py_compile
import tempfile
from pathlib import Path


def _can_compile(code: str) -> bool:
    """Return True if code snippet compiles."""
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        return True
    except py_compile.PyCompileError:
        return False
    finally:
        os.unlink(tmp_path)


def select_snippet(snippets: list[str]) -> str:
    """Select the first compilable snippet or fallback to the first."""
    for code in snippets:
        if _can_compile(code):
            return code
    return snippets[0] if snippets else ""


def merge_teacher_outputs(input_path: Path, output_path: Path) -> None:
    with input_path.open('r', encoding='utf-8') as fin, output_path.open('w', encoding='utf-8') as fout:
        for line in fin:
            if not line.strip():
                continue
            data = json.loads(line)
            teachers = data.get('teachers', {})
            chosen = select_snippet(list(teachers.values()))
            out = {"prompt": data.get('prompt', ''), "completion": chosen}
            fout.write(json.dumps(out) + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Merge teacher outputs")
    parser.add_argument('--input', default='modules/reasoner/teacher_outputs.jsonl')
    parser.add_argument('--output', default='modules/reasoner/distill_data.jsonl')
    args = parser.parse_args(argv)
    merge_teacher_outputs(Path(args.input), Path(args.output))


if __name__ == '__main__':
    main()
