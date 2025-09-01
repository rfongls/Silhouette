import argparse
import json
from pathlib import Path

from .dsl_parser import parse_dsl_file


def get_denials(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = parse_dsl_file(path)
    deny = data.get("limits", {}).get("deny_on", "")
    return [d.strip().lower() for d in deny.split(",") if d.strip()]


def audit_memory(memory: Path, persona: Path) -> list[str]:
    violations = []
    denials = get_denials(persona)
    if not denials or not memory.exists():
        return violations
    for i, line in enumerate(memory.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = entry.get("content", "").lower()
        for d in denials:
            if d in text:
                violations.append(f"Line {i}: found '{d}'")
    return violations


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit memory against persona")
    parser.add_argument("--persona", default="persona.dsl")
    parser.add_argument("--memory", default="memory.jsonl")
    args = parser.parse_args(argv)

    viols = audit_memory(Path(args.memory), Path(args.persona))
    if viols:
        print("Persona violations:")
        for v in viols:
            print("  ", v)
    else:
        print("No persona violations detected.")


if __name__ == "__main__":
    main()
