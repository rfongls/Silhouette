import json
from typing import Iterable, Dict
from .base_adapter import BaseAdapter

class JSONLAdapter(BaseAdapter):
    """
    Reads JSONL where each line is a JSON object with keys:
      instruction, input, output, tools_used (optional list)
    """
    def __init__(self, path: str):
        self.path = path

    def samples(self) -> Iterable[Dict]:
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                yield {
                    "instruction": ex.get("instruction", ""),
                    "input": ex.get("input", ""),
                    "output": ex.get("output", ""),
                    "tools_used": ex.get("tools_used", []),
                }
