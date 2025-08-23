from __future__ import annotations
from typing import List
from .batch import unwrap_batch


def normalize_cr(text: str) -> str:
    return "\r".join(text.replace("\r\n", "\n").replace("\r", "\n").split("\n")) + ("\r" if not text.endswith("\r") else "")


def split_messages(text: str) -> List[str]:
    t = text.strip()
    if t.startswith(("FHS|", "BHS|")):
        return unwrap_batch(t)
    lines = t.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    parts, cur = [], []
    for ln in lines:
        if ln.startswith("MSH|") and cur:
            parts.append("\r".join(cur) + "\r")
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        parts.append("\r".join(cur) + "\r")
    return parts
