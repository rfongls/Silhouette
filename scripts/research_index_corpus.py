#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys


def main(root="docs/corpus"):
    root = pathlib.Path(root)
    pdfs = sorted(root.glob("*.pdf"))
    ok = 0
    for p in pdfs:
        read_out = subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from skills.research_read_pdf.v1.wrapper import tool; import sys; print(tool(sys.argv[1]))",
                str(p),
            ]
        )
        subprocess.check_call(
            [
                sys.executable,
                "-c",
                "from skills.research_index.v1.wrapper import tool; import sys; print(tool(sys.stdin.read()))",
            ],
            input=read_out,
            text=True,
        )
        ok += 1
    print(f"Indexed {ok} PDFs into artifacts/index/research.db")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/corpus")

