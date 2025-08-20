import sys
import re
import subprocess
import tempfile
import os
import pathlib

MMDC = "mmdc"

def export_mermaid(md_path: pathlib.Path):
    text = md_path.read_text(encoding="utf-8")
    blocks = list(re.finditer(r"```mermaid\n(.*?)\n```", text, re.DOTALL))
    out_dir = md_path.parent / "svg"
    out_dir.mkdir(exist_ok=True)
    for i, m in enumerate(blocks, 1):
        code = m.group(1)
        with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        svg_path = out_dir / f"{md_path.stem}_{i}.svg"
        try:
            subprocess.run([MMDC, "-i", tmp_path, "-o", str(svg_path), "-b", "transparent"], check=True)
            print(f"Exported {svg_path}")
        finally:
            os.unlink(tmp_path)

def walk_docs(root: str):
    for p in pathlib.Path(root).rglob("*.md"):
        export_mermaid(p)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: export_mermaid.py <docs_root>")
        sys.exit(1)
    walk_docs(sys.argv[1])
