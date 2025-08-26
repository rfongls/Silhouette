#!/usr/bin/env python
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
import sys, csv, json, argparse, warnings, re
from collections import Counter
from datetime import datetime

try:
    from hl7apy.parser import parse_message
    from hl7apy.exceptions import HL7apyException
except ModuleNotFoundError:
    print("hl7apy is not installed. Install with: py -m pip install hl7apy")
    sys.exit(1)

# ---------------- IO & normalization ----------------

def normalize_hl7_text(data: bytes) -> str:
    txt = data.decode("latin-1", errors="ignore")
    txt = txt.replace("\x0b", "").replace("\x1c\r", "")  # strip MLLP if present
    txt = txt.replace("\r\n", "\r").replace("\n", "\r").replace("\r\r", "\r")
    return txt

def strip_batch_envelopes(txt: str) -> str:
    return re.sub(r'^(?:FHS|BHS|BTS|FTS)\|.*\r?', "", txt, flags=re.MULTILINE)

def split_messages(txt: str) -> List[str]:
    if not txt:
        return []
    txt = strip_batch_envelopes(txt)
    if not txt.endswith("\r"):
        txt += "\r"
    parts = re.split(r'(?=^MSH\|)', txt, flags=re.MULTILINE)
    msgs = [p.strip() for p in parts if p.strip()]
    return [m if m.endswith("\r") else (m + "\r") for m in msgs]

# ---------------- helpers & separators ----------------

def first_segment(msg, name: str):
    for s in msg.children:
        if getattr(s, "name", "") == name:
            return s
    return None

def segment_counts(msg) -> Dict[str, int]:
    return dict(Counter(s.name for s in msg.children if hasattr(s, "name")))

def safe_get_er7(component, attr: str, default: str = "") -> str:
    try:
        return getattr(component, attr).to_er7() if hasattr(component, attr) else default
    except Exception:
        return default

def get_msg_type_and_event(msh) -> Tuple[str, str]:
    raw = safe_get_er7(msh, "msh_9", "")
    parts = raw.split("^") if raw else []
    return (parts[0] if len(parts) >= 1 else "",
            parts[1] if len(parts) >= 2 else "")

def count_segments(msg, name: str) -> int:
    return sum(1 for s in msg.children if getattr(s, "name", "") == name)

def get_separators(msh) -> Tuple[str, str, str, str, str]:
    fs = safe_get_er7(msh, "msh_1", "|")
    enc = safe_get_er7(msh, "msh_2", "^~\\&")
    comp = enc[0] if len(enc) > 0 else "^"
    rep  = enc[1] if len(enc) > 1 else "~"
    esc  = enc[2] if len(enc) > 2 else "\\"
    sub  = enc[3] if len(enc) > 3 else "&"
    return fs, comp, rep, esc, sub

def get_cwe_component(raw: str, comp_idx: int, sub_idx: Optional[int], comp_sep: str, sub_sep: str) -> str:
    if not raw or comp_idx <= 0:
        return ""
    comps = raw.split(comp_sep)
    if comp_idx > len(comps):
        return ""
    comp = comps[comp_idx - 1]
    if sub_idx is None:
        return comp
    subs = comp.split(sub_sep)
    if sub_idx <= 0 or sub_idx > len(subs):
        return ""
    return subs[sub_idx - 1]

# -------------
