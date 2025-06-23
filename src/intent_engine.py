"""Intent detection engine placeholder."""

import json
from pathlib import Path

EXAMPLES_FILE = Path("INTENT_EXAMPLES.json")


def load_examples():
    """Load intent examples from the reference file."""
    if not EXAMPLES_FILE.exists():
        return []
    with open(EXAMPLES_FILE, "r") as f:
        data = json.load(f)
    return data.get("examples", [])


def detect_intent(text: str) -> str:
    """Very simple phrase match intent detection."""
    examples = load_examples()
    for ex in examples:
        if ex["phrase"].lower() in text.lower():
            return ex["intent"]
    return "unknown"