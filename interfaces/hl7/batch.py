from __future__ import annotations
from typing import List


def wrap_batch(messages: List[str]) -> str:
    header = "FHS|^~\\&\rBHS|^~\\&\r"
    body = "".join(messages)
    trailer = f"BTS|{len(messages)}\rFTS|1\r"
    return header + body + trailer


def unwrap_batch(batch: str) -> List[str]:
    lines = batch.split("\r")
    msgs, cur = [], []
    for ln in lines:
        if ln.startswith("MSH|"):
            if cur:
                msgs.append("\r".join(cur) + "\r")
                cur = [ln]
            else:
                cur = [ln]
        elif ln.startswith("BTS|") or ln.startswith("FTS|"):
            if cur:
                msgs.append("\r".join(cur) + "\r")
                cur = []
        else:
            if cur:
                cur.append(ln)
    if cur:
        msgs.append("\r".join(cur) + "\r")
    return msgs
