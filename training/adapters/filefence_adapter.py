import json
import pathlib
from typing import Iterable, Dict
from .base_adapter import BaseAdapter

class FileFenceAdapter(BaseAdapter):
    """Converts files[] entries into file-fence output blocks."""
    def __init__(self, path: str):
        self.path = pathlib.Path(path)

    def _lang_for(self, path: str) -> str:
        ext = pathlib.Path(path).suffix.lower()
        return {
            ".py": "python",
            ".kt": "kotlin",
            ".java": "java",
            ".cs": "csharp",
            ".html": "html",
            ".xml": "xml",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".md": "markdown",
            ".txt": "text",
        }.get(ext, "")

    def samples(self) -> Iterable[Dict]:
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                fences = []
                for fobj in ex.get("files", []):
                    lang = self._lang_for(fobj.get("path", ""))
                    fences.append(f"```file: {fobj['path']}\n```{lang}\n{fobj['content']}\n```")
                yield {
                    "instruction": ex.get("instruction", ""),
                    "input": ex.get("input", ""),
                    "output": "\n\n".join(fences),
                    "tools_used": ex.get("tags", []),
                }
