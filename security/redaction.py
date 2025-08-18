import pathlib
import re
from typing import Any
import yaml

_DEFAULT_RULES = pathlib.Path(__file__).with_name("redaction_rules.yaml")

class Redactor:
    """Redact sensitive info based on regex rules."""
    def __init__(self, rules_path: pathlib.Path | None = None):
        path = rules_path or _DEFAULT_RULES
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            data = {}
        self.patterns = []
        for p in data.get("patterns", []):
            try:
                self.patterns.append((re.compile(p.get("regex", ""), re.IGNORECASE), p.get("replace", "REDACTED")))
            except re.error:
                continue

    def redact_text(self, text: str | None) -> str | None:
        if not text:
            return text
        for reg, repl in self.patterns:
            text = reg.sub(repl, text)
        return text

    def redact_obj(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self.redact_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.redact_obj(v) for v in obj]
        if isinstance(obj, str):
            return self.redact_text(obj)
        return obj

# convenience default redactor
DEFAULT_REDACTOR = Redactor()
