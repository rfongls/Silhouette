#!/usr/bin/env python
"""
HL7 batch parser + QA (per-message, strict TS, domain checks) with rules.yaml auto-discovery

Features
- Splits batched HL7 files into individual messages (handles FHS/BHS and MLLP framing)
- Reads separators from MSH-1/MSH-2; validates repetitions (~), components (^) and ranges (start^end)
- Message-type–aware required-segment rules (ORU/ORM/OML/MDM/RDE/VXU)
- Strict timestamps: only YYYYMMDD or YYYYMMDDHHMMSS (optional literal 'T')
- Results profile checks: OBR-24 allowed set, OBR-4 codedness, OBR-25 status, OBR-2/3 presence,
  OBX-3 codedness, OBX-11 status (allowed set), OBX-5 required policy, OBX-2 vs OBX-5 type checks
- MDM profile checks: TXA-2 coded (2.1 id, 2.3 system, capture 2.3.2), TXA-6 timestamp
- PID-3 (CX) shape checks: .1 id and at least one of .4 authority or .5 id type across repetitions
- Configurable via rules.yaml with auto-discovery:
    1) nearest rules.yaml/hl7_rules.yaml up the tree from input path
    2) repo/tests/hl7/rules.yaml (preferred with fixtures)
    3) repo/config/hl7_rules.yaml (org defaults)
- CSV output: one row per message with trace, normalized dates, rule issues, and domain extras
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set, Iterable
import sys, csv, json, argparse, warnings, re, copy, os
from collections import Counter
from datetime import datetime

# Optional dependency: PyYAML (rules file). Falls back to built-in defaults if missing.
try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None  # we’ll proceed with DEFAULT_RULES

# hl7apy is required
try:
    from hl7apy.parser import parse_message
    from hl7apy.exceptions import HL7apyException
except ModuleNotFoundError:
    print("hl7apy is not installed. Install with: py -m pip install hl7apy")
    sys.exit(1)

# ---------------- Default sets and default rules (used if rules file is absent) ----------------

DEFAULT_OBR24_ALLOWED: Set[str] = {
    "CH","CO","HEM","MB","MIC","IMM","LAB","PATH",
    "RAD","CT","MR","US","XR","NM"
}
DEFAULT_RESULT_STATUS: Set[str] = {"F","C","I","P","R","S","U","D","X","W"}
DEFAULT_OBX11_EMPTY_ALLOWS: Set[str] = {"X","I","W","U"}

DEFAULT_RULES: Dict[str, Any] = {
    "profiles": {
        "results": {
            "types": ["ORU","ORM","OML"],
            "timestamps": {"strict": True, "fail_on_dtm": True},
            "allowed": {
                "obr24": list(DEFAULT_OBR24_ALLOWED),
                "result_status": list(DEFAULT_RESULT_STATUS),        # used for OBR-25 and OBX-11
                "obx11_empty_allows": list(DEFAULT_OBX11_EMPTY_ALLOWS),
            },
            "policies": {
                "require_pid3_shape": True,                         # PID-3: .1 and (.4 or .5)
                "require_obr2_or_obr3": True,                       # at least one of OBR-2/OBR-3
                "obr4_coded": True,                                 # OBR-4 has .1 id AND .3 system
                "obr25_allowed": True,                              # OBR-25 must be in allowed result_status
                "obx11_allowed": True,                              # OBX-11 must be in allowed result_status
                "obx3_coded": True,                                 # OBX-3 has .1 id AND .3 system
                "obx5_required_unless_status_in_empty_allows": True,
                "obx2_vs_obx5_typecheck": True,                     # NM numeric, DT/DTM/TS TS-valid, CE/CWE coded, SN basic numeric
            },
        },
        "mdm": {
            "types": ["MDM"],
            "timestamps": {"strict": True, "fail_on_dtm": False},
            "allowed": {},
            "policies": {
                "require_pid3_shape": True,
                "txa2_coded": True,                                 # TXA-2 has .1 id and .3 system
            },
        },
    },
    "default_profile": "results",
}

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

# ---------------- strict timestamps (YYYYMMDD / YYYYMMDDHHMMSS) ----------------

def ts_is_valid_strict(value: str) -> bool:
    if not value:
        return False
    v = value.strip().replace("T", "")
    if not v.isdigit():
        return False
    try:
        if len(v) == 8:
            datetime.strptime(v, "%Y%m%d"); return True
        if len(v) == 14:
            datetime.strptime(v, "%Y%m%d%H%M%S"); return True
        return False
    except ValueError:
        return False

def ts_normalize_strict(value: str) -> str:
    if not value:
        return ""
    v = value.strip().replace("T", "")
    if not v.isdigit():
        return ""
    try:
        if len(v) == 8:
            return datetime.strptime(v, "%Y%m%d").strftime("%Y-%m-%d")
        if len(v) == 14:
            return datetime.strptime(v, "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""
    return ""

def _check_ts_reps(raw: str, base_label: str, comp_sep: str, rep_sep: str, issues: List[str], norm_key: Optional[str], norms: Dict[str, str]):
    if not raw:
        return
    reps = raw.split(rep_sep)
    many = len(reps) > 1
    for idx, r in enumerate(reps, start=1):
        label = f"{base_label}[{idx}]" if many else base_label
        if comp_sep in r:  # DR-style range: start^end
            parts = r.split(comp_sep)
            start = parts[0] if len(parts) >= 1 else ""
            end   = parts[1] if len(parts) >= 2 else ""
            if start and not ts_is_valid_strict(start):
                issues.append(f"{label} start invalid TS: {start}")
            if end and not ts_is_valid_strict(end):
                issues.append(f"{label} end invalid TS: {end}")
        else:
            if not ts_is_valid_strict(r):
                issues.append(f"{label} invalid TS: {r}")
            else:
                if norm_key and idx == 1:
                    norms[norm_key] = ts_normalize_strict(r)

def collect_ts_field_issues_and_norms(msg) -> Tuple[List[str], Dict[str, str]]:
    issues: List[str] = []
    norms: Dict[str, str] = {}
    msh = first_segment(msg, "MSH")
    fs, comp_sep, rep_sep, esc, sub = get_separators(msh)
    def chk(seg, field_attr, label, norm_key: Optional[str] = None):
        if not seg: return
        raw = safe_get_er7(seg, field_attr, "")
        _check_ts_reps(raw, label, comp_sep, rep_sep, issues, norm_key, norms)

    pid = first_segment(msg, "PID")
    chk(msh, "msh_7", "MSH-7 (Date/Time of Message)", norm_key="msh7_norm")
    chk(pid, "pid_7", "PID-7 (Date/Time of Birth)",    norm_key="pid7_norm")

    for seg in (s for s in msg.children if getattr(s, "name", "") == "OBR"):
        chk(seg, "obr_6",  "OBR-6 (Requested Date/Time)")
        chk(seg, "obr_7",  "OBR-7 (Observation Date/Time)")
        chk(seg, "obr_14", "OBR-14 (Specimen Received Date/Time)")
        chk(seg, "obr_22", "OBR-22 (Results Rpt/Status Chg Date/Time)")

    for seg in (s for s in msg.children if getattr(s, "name", "") == "OBX"):
        chk(seg, "obx_14", "OBX-14 (Date/Time of Observation)")

    for seg in (s for s in msg.children if getattr(s, "name", "") == "RXA"):
        chk(seg, "rxa_3", "RXA-3 (Start of Admin)")
        chk(seg, "rxa_4", "RXA-4 (End of Admin)")

    for seg in (s for s in msg.children if getattr(s, "name", "") == "TXA"):
        chk(seg, "txa_6", "TXA-6 (Transcription Date/Time)")

    return issues, norms

# ---------------- baseline type rules ----------------

def qa_rules_by_type(msg, msh, pid) -> List[str]:
    issues: List[str] = []
    if not msh:
        return ["MSH missing"]
    if not pid:
        issues.append("PID missing")

    mt, _ = get_msg_type_and_event(msh)
    mt = (mt or "").upper()

    obr_n = count_segments(msg, "OBR")
    obx_n = count_segments(msg, "OBX")
    txa_n = count_segments(msg, "TXA")
    rxe_n = count_segments(msg, "RXE")
    rxa_n = count_segments(msg, "RXA")

    if mt == "ORU":
        if obr_n == 0: issues.append("OBR missing (required for ORU)")
        if obx_n == 0: issues.append("OBX missing (required for ORU results)")
    elif mt in {"ORM", "OML"}:
        if obr_n == 0: issues.append("OBR missing (required for ORM/OML)")
    elif mt == "MDM":
        if txa_n == 0: issues.append("TXA missing (required for MDM)")
    elif mt == "RDE":
        if rxe_n == 0: issues.append("RXE missing (required for RDE)")
    elif mt == "VXU":
        if rxa_n == 0: issues.append("RXA missing (required for VXU)")
    return issues

# ---------------- domain checks (results & MDM) ----------------

NUM_RE = re.compile(r'^[+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?$')
def _is_numeric(v: str) -> bool:
    return bool(NUM_RE.match(v.strip()))

def _split_reps(raw: str, rep_sep: str) -> List[str]:
    if not raw:
        return []
    return [x for x in (s.strip() for s in raw.split(rep_sep)) if x != ""]

def _obx_ce_cwe_coded_ok(raw: str, comp: str, sub: str) -> bool:
    id_  = get_cwe_component(raw, 1, None, comp, sub)
    sys_ = get_cwe_component(raw, 3, None, comp, sub)
    return bool(id_) and bool(sys_)

def _pid3_shape_issues(pid3_raw: str, comp: str, rep: str, sub: str) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    reps = pid3_raw.split(rep) if pid3_raw else []
    if not reps:
        return False, ["PID-3 empty"]
    any_ok = False
    for i, r in enumerate(reps, start=1):
        comps = r.split(comp) if r else []
        id_num = comps[0] if len(comps) >= 1 else ""
        auth   = comps[3] if len(comps) >= 4 else ""  # HD
        idtype = comps[4] if len(comps) >= 5 else ""
        ok = bool(id_num) and (bool(auth) or bool(idtype))
        if not ok:
            missing = []
            if not id_num: missing.append("3.1 id")
            if not (auth or idtype): missing.append("3.4 authority or 3.5 id_type")
            issues.append(f"PID-3[{i}] missing: {', '.join(missing)}")
        any_ok = any_ok or ok
    return any_ok, issues

def collect_domain_issues(
    msg,
    profile_name: str,
    allow_obr24: Optional[Set[str]],
    allow_obx11: Optional[Set[str]],
    allow_obr25: Optional[Set[str]],
    obx11_empty_allows: Optional[Set[str]],
    policies: Dict[str, bool],
) -> Tuple[List[str], Dict[str, Any], List[str]]:
    """
    Returns (issues, extras, obx_issues)
    """
    issues: List[str] = []
    obx_issues: List[str] = []
    extras: Dict[str, Any] = {
        "obr24_values": "", "obx11_values": "", "obr25_values": "",
        "txa2_id": "", "txa2_text": "", "txa2_system": "", "txa2_3_2": "",
        "pid3_shape_ok": "N", "pid3_shape_issues_joined": "",
    }

    msh = first_segment(msg, "MSH")
    fs, comp, rep, esc, sub = get_separators(msh)
    pid = first_segment(msg, "PID")

    # PID-3 shape
    if policies.get("require_pid3_shape", True) and pid:
        pid3_raw = safe_get_er7(pid, "pid_3", "")
        ok, pid3_issues = _pid3_shape_issues(pid3_raw, comp, rep, sub)
        extras["pid3_shape_ok"] = "Y" if ok else "N"
        extras["pid3_shape_issues_joined"] = "; ".join(pid3_issues) if pid3_issues else ""

    # RESULTS profile rules
    if profile_name == "results":
        # OBR-level
        seen_obr24: Set[str] = set()
        seen_obr25: Set[str] = set()
        obr_list = [s for s in msg.children if getattr(s, "name", "") == "OBR"]
        for idx, seg in enumerate(obr_list, start=1):
            raw24 = safe_get_er7(seg, "obr_24", "")
            for val in _split_reps(raw24, rep):
                seen_obr24.add(val)
             if allow_obr24 and val not in allow_obr24:
                issues.append(f"OBR[{idx}]-24 unexpected value: {val}")


            # OBR-4 codedness
            if policies.get("obr4_coded", True):
                raw4 = safe_get_er7(seg, "obr_4", "")
                id_  = get_cwe_component(raw4, 1, None, comp, sub)
                sys_ = get_cwe_component(raw4, 3, None, comp, sub)
                if not id_: issues.append(f"OBR[{idx}]-4.1 (Universal Service ID) missing")
                if not sys_: issues.append(f"OBR[{idx}]-4.3 (Coding System) missing")

            # OBR-25 allowed
            raw25 = safe_get_er7(seg, "obr_25", "")
            if raw25:
                for v in _split_reps(raw25, rep):
                    seen_obr25.add(v)
                    if policies.get("obr25_allowed", True) and allow_obr25 and v not in allow_obr25:
                        issues.append(f"OBR[{idx}]-25 unexpected status: {v}")
            else:
                issues.append(f"OBR[{idx}]-25 (Result Status) missing")

            # OBR-2/OBR-3 at least one
            if policies.get("require_obr2_or_obr3", True):
                has2 = bool(safe_get_er7(seg, "obr_2", ""))
                has3 = bool(safe_get_er7(seg, "obr_3", ""))
                if not (has2 or has3):
                    issues.append(f"OBR[{idx}] both OBR-2 (Placer) and OBR-3 (Filler) are missing (need at least one)")

        extras["obr24_values"] = ",".join(sorted(seen_obr24)) if seen_obr24 else ""
        extras["obr25_values"] = ",".join(sorted(seen_obr25)) if seen_obr25 else ""

        # OBX-level
        seen_obx11: Set[str] = set()
        obx_list = [s for s in msg.children if getattr(s, "name", "") == "OBX"]
        for j, seg in enumerate(obx_list, start=1):
            vt = safe_get_er7(seg, "obx_2", "").upper()
            obx3 = safe_get_er7(seg, "obx_3", "")
            obx5 = safe_get_er7(seg, "obx_5", "")
            obx11 = safe_get_er7(seg, "obx_11", "")

            # OBX-11
            obx11_vals = _split_reps(obx11, rep)
            if not obx11_vals:
                obx_issues.append(f"OBX[{j}]-11 (Result Status) missing")
            else:
                for v in obx11_vals:
                    seen_obx11.add(v)
                    if policies.get("obx11_allowed", True) and allow_obx11 and v not in allow_obx11:
                        obx_issues.append(f"OBX[{j}]-11 unexpected status: {v}")

            empty_allowed = any(v in (obx11_empty_allows or set()) for v in obx11_vals) if obx11_vals else False

            # OBX-3 codedness
            if policies.get("obx3_coded", True):
                if not _obx_ce_cwe_coded_ok(obx3, comp, sub):
                    obx_issues.append(f"OBX[{j}]-3 codedness missing (id/system)")

            # OBX-5 required policy
            if policies.get("obx5_required_unless_status_in_empty_allows", True):
                if not obx5 and not empty_allowed:
                    obx_issues.append(f"OBX[{j}]-5 (Observation Value) missing")

            # OBX-2 vs OBX-5
            if policies.get("obx2_vs_obx5_typecheck", True) and obx5:
                vals = _split_reps(obx5, rep)
                if vt in {"NM"}:
                    for k, v in enumerate(vals, start=1):
                        if not _is_numeric(v):
                            obx_issues.append(f"OBX[{j}]-5[{k}] not numeric for NM")
                elif vt in {"DT", "DTM", "TS"}:
                    for k, v in enumerate(vals, start=1):
                        # allow DR style start^end
                        if comp in v:
                            s, e = (v.split(comp) + ["",""])[:2]
                            if s and not ts_is_valid_strict(s):
                                obx_issues.append(f"OBX[{j}]-5[{k}] start invalid TS: {s}")
                            if e and not ts_is_valid_strict(e):
                                obx_issues.append(f"OBX[{j}]-5[{k}] end invalid TS: {e}")
                        else:
                            if not ts_is_valid_strict(v):
                                obx_issues.append(f"OBX[{j}]-5[{k}] invalid TS")
                elif vt in {"CE","CWE"}:
                    for k, v in enumerate(vals, start=1):
                        id_  = get_cwe_component(v, 1, None, comp, sub)
                        sys_ = get_cwe_component(v, 3, None, comp, sub)
                        if not id_ or not sys_:
                            obx_issues.append(f"OBX[{j}]-5[{k}] CE/CWE codedness missing (id/system)")
                elif vt == "SN":
                    for k, v in enumerate(vals, start=1):
                        comps = v.split(comp)
                        num1 = comps[1] if len(comps) >= 2 else ""
                        if num1 and not _is_numeric(num1):
                            obx_issues.append(f"OBX[{j}]-5[{k}] SN numeric part not numeric")

        extras["obx11_values"] = ",".join(sorted(seen_obx11)) if seen_obx11 else ""

    # MDM profile
    if profile_name == "mdm":
        txa = first_segment(msg, "TXA")
        if txa:
            raw2 = safe_get_er7(txa, "txa_2", "")
            extras["txa2_id"]     = get_cwe_component(raw2, 1, None, comp, sub)
            extras["txa2_text"]   = get_cwe_component(raw2, 2, None, comp, sub)
            extras["txa2_system"] = get_cwe_component(raw2, 3, None, comp, sub)
            extras["txa2_3_2"]    = get_cwe_component(raw2, 3, 2,    comp, sub)
            if policies.get("txa2_coded", True):
                if not extras["txa2_id"]:
                    issues.append("TXA-2.1 (Document Type ID) missing")
                if not extras["txa2_system"]:
                    issues.append("TXA-2.3 (Coding System) missing")

    return issues, extras, obx_issues

# ---------------- rules loading & profile resolution ----------------

def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def find_repo_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent

def discover_rule_candidates(input_target: Path) -> List[Path]:
    root = input_target if input_target.is_dir() else input_target.parent
    repo = find_repo_root(root) or root

    candidates: List[Path] = []
    # nearest-first in the input tree
    cur = root
    while True:
        for name in ("rules.yaml", "hl7_rules.yaml"):
            p = cur / name
            if p.exists():
                candidates.append(p)
        if cur.parent == cur:
            break
        cur = cur.parent

    # repo-level conventional locations (tests override before config)
    for p in [repo / "tests" / "hl7" / "rules.yaml",
              repo / "tests" / "hl7" / "hl7_rules.yaml",
              repo / "config" / "hl7_rules.yaml",
              repo / "config" / "rules.yaml"]:
        if p.exists():
            candidates.append(p)

    # de-dup while preserving order
    seen = set()
    uniq = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq

def load_rules_chain(paths: Iterable[Path]) -> Dict[str, Any]:
    rules = copy.deepcopy(DEFAULT_RULES)
    if yaml is None:
        return rules
    for p in paths:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                rules = _deep_merge(rules, data)
        except Exception:
            # ignore unreadable entries; keep going
            pass
    return rules

def load_rules(path: Optional[Path]) -> Dict[str, Any]:
    rules = copy.deepcopy(DEFAULT_RULES)
    if not path:
        return rules
    if not path.exists() or not path.is_file():
        return rules
    if yaml is None:
        return rules
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            rules = _deep_merge(rules, data)
    except Exception:
        pass
    return rules

def resolve_profile_for_msg(msh, rules: Dict[str, Any], forced_profile: Optional[str]) -> str:
    if forced_profile and forced_profile != "auto":
        return forced_profile
    mt, _ = get_msg_type_and_event(msh)
    mt = (mt or "").upper()
    profiles = rules.get("profiles", {})
    for name, cfg in profiles.items():
        types = [t.upper() for t in cfg.get("types", [])]
        if mt in types:
            return name
    return rules.get("default_profile", "results")

# ---------------- per-message QA ----------------

def qa_one_message(
    raw_msg: str,
    rules: Dict[str, Any],
    forced_profile: Optional[str] = None,
    quiet_parse: bool = False,
    cli_fail_on_dtm: Optional[bool] = None,
) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "status": "ok", "error": "",
        "issues": [], "dtm_issues": [], "domain_issues": [], "obx_issues": [],
        "msg_type": "", "msg_event": "",
        "msh_3": "", "msh_4": "", "msh_10": "",
        "pid_3": "", "msh7_norm": "", "pid7_norm": "",
        "obr_count": 0, "obx_count": 0, "seg_counts": {},
        # domain extras:
        "obr24_values": "", "obx11_values": "", "obr25_values": "",
        "txa2_id": "", "txa2_text": "", "txa2_system": "", "txa2_3_2": "",
        "pid3_shape_ok": "N", "pid3_shape_issues_joined": "",
    }
    if quiet_parse:
        warnings.filterwarnings("ignore")

    try:
        msg = parse_message(raw_msg, find_groups=False)
    except HL7apyException as e:
        res["status"] = "parse_error"; res["error"] = str(e); return res
    except Exception as e:
        res["status"] = "parse_error"; res["error"] = f"unexpected parse error: {e}"; return res

    msh = first_segment(msg, "MSH")
    pid = first_segment(msg, "PID")

    if msh:
        res["msh_3"]  = safe_get_er7(msh, "msh_3", "<MSH-3 missing>")
        res["msh_4"]  = safe_get_er7(msh, "msh_4", "<MSH-4 missing>")
        res["msh_10"] = safe_get_er7(msh, "msh_10", "<MSH-10 missing>")
        mt, me = get_msg_type_and_event(msh)
        res["msg_type"], res["msg_event"] = mt, me
    if pid:
        res["pid_3"] = safe_get_er7(pid, "pid_3", "<PID-3 missing>")

    res["seg_counts"] = segment_counts(msg)
    res["obr_count"] = res["seg_counts"].get("OBR", 0)
    res["obx_count"] = res["seg_counts"].get("OBX", 0)

    # 1) baseline type rules
    res["issues"] = qa_rules_by_type(msg, msh, pid)

    # 2) resolve profile + settings from rules
    prof_name = resolve_profile_for_msg(msh, rules, forced_profile)
    prof_cfg = rules.get("profiles", {}).get(prof_name, {})
    allowed = prof_cfg.get("allowed", {})
    policies = prof_cfg.get("policies", {})
    ts_cfg = prof_cfg.get("timestamps", {"strict": True, "fail_on_dtm": False})

    allow_obr24 = set(allowed.get("obr24", DEFAULT_OBR24_ALLOWED))
    allow_status = set(allowed.get("result_status", DEFAULT_RESULT_STATUS))
    empty_allows = set(allowed.get("obx11_empty_allows", DEFAULT_OBX11_EMPTY_ALLOWS))

    # 3) timestamps (strict) — only run if enabled
    if ts_cfg.get("strict", True):
        dtm_issues, norms = collect_ts_field_issues_and_norms(msg)
        res["dtm_issues"] = dtm_issues
        res["msh7_norm"] = norms.get("msh7_norm", "")
        res["pid7_norm"] = norms.get("pid7_norm", "")
        fail_on_dtm = ts_cfg.get("fail_on_dtm", False) if cli_fail_on_dtm is None else cli_fail_on_dtm
    if fail_on_dtm and dtm_issues and res["status"] == "ok":
        res["status"] = "value_error"


    # 4) domain + OBX checks per profile
    dom_issues, extras, obx_issues = collect_domain_issues(
        msg,
        profile_name=prof_name,
        allow_obr24=allow_obr24,
        allow_obx11=allow_status,
        allow_obr25=allow_status,
        obx11_empty_allows=empty_allows,
        policies=policies,
    )
    res["domain_issues"] = dom_issues
    res["obx_issues"] = obx_issues
    for k, v in extras.items():
        res[k] = v

    # escalate to value_error if domain or obx issues present
    if (dom_issues or obx_issues) and res["status"] == "ok":
        res["status"] = "value_error"

    return res

# ---------------- per-file driver ----------------

def qa_one_file(
    path: Path,
    rules: Dict[str, Any],
    forced_profile: Optional[str],
    quiet_parse: bool,
    cli_fail_on_dtm: Optional[bool],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    rows: List[Dict[str, Any]] = []
    summary = {"total": 0, "ok": 0, "errors": 0}

    try:
        data = path.read_bytes()
    except Exception as e:
        rows.append({
            "file": str(path), "message_index": "",
            "status": "read_error", "error": f"read failed: {e}",
        })
        summary["total"] += 1; summary["errors"] += 1
        return rows, summary

    txt = normalize_hl7_text(data)
    messages = split_messages(txt) or [txt]

    for i, raw_msg in enumerate(messages, start=1):
        res = qa_one_message(
            raw_msg,
            rules=rules,
            forced_profile=forced_profile,
            quiet_parse=quiet_parse,
            cli_fail_on_dtm=cli_fail_on_dtm,
        )
        res["file"] = str(path)
        res["message_index"] = i
        rows.append(res)
        summary["total"] += 1
        if res["status"] == "ok":
            summary["ok"] += 1
        else:
            summary["errors"] += 1

    return rows, summary

# ---------------- CSV & CLI ----------------

CSV_FIELDS = [
    "file", "message_index",
    "status", "error",
    "msg_type", "msg_event",
    "issues_joined", "dtm_issues_joined", "domain_issues_joined", "obx_issues_joined",
    "msh_3", "msh_4", "msh_10", "pid_3",
    "pid3_shape_ok", "pid3_shape_issues_joined",
    "msh7_norm", "pid7_norm",
    "obr_count", "obx_count",
    "obr24_values", "obr25_values", "obx11_values",
    "txa2_id", "txa2_text", "txa2_system", "txa2_3_2",
    "seg_counts_str",
]

def write_csv(out_path: Path, rows: List[Dict[str, Any]]) -> Path:
    for r in rows:
        r["issues_joined"]        = "; ".join(r.get("issues", [])) if r.get("issues") else ""
        r["dtm_issues_joined"]    = "; ".join(r.get("dtm_issues", [])) if r.get("dtm_issues") else ""
        r["domain_issues_joined"] = "; ".join(r.get("domain_issues", [])) if r.get("domain_issues") else ""
        r["obx_issues_joined"]    = "; ".join(r.get("obx_issues", [])) if r.get("obx_issues") else ""
        r["seg_counts_str"]       = ", ".join(f"{k}:{v}" for k, v in (r.get("seg_counts") or {}).items())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    return out_path

def collect_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    return sorted([p for p in target.rglob("*.hl7") if p.is_file()])

def run_cli(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="HL7 batch parser + QA (per-message, strict TS, domain checks, rules.yaml)")
    ap.add_argument("path", help="HL7 file or directory")
    ap.add_argument("--report", help="CSV output path (default: alongside input)")
    ap.add_argument("--json", dest="as_json", action="store_true", help="Emit results as JSON to stdout")
    ap.add_argument("--fail-on-dtm", action="store_true", help="Override rules: mark message as value_error if any strict timestamp is invalid")
    ap.add_argument("--quiet-parse", action="store_true", help="Suppress parser warnings/noise")
    ap.add_argument("--max-print", type=int, default=10, help="Max messages to print per file (console summary)")
    ap.add_argument("--verbose", action="store_true", help="Print every message (overrides --max-print)")
    ap.add_argument("--rules", default="auto",
                    help="Path to rules.yaml, or 'auto' to search near input and under tests/hl7/ and config/.")
    ap.add_argument("--dump-rules", action="store_true", help="Print effective merged rules to stdout and exit")

    args = ap.parse_args(argv[1:])

    target = Path(args.path)
    files = collect_files(target)
    if not files:
        print(f"No .hl7 files found under: {target}")
        return 3

    # load rules (auto or explicit)
    if args.rules != "auto":
        rules_path = Path(args.rules)
        rules = load_rules(rules_path)
        print(f"[rules] using: {rules_path}")
    else:
        candidates = discover_rule_candidates(target)
        if candidates:
            rules = load_rules_chain(candidates)
            print(f"[rules] using: {', '.join(str(p) for p in candidates)}")
        else:
            rules = copy.deepcopy(DEFAULT_RULES)
            print("[rules] no rules.yaml found; using built-in defaults")

    if args.dump_rules:
        print(json.dumps(rules, ensure_ascii=False, indent=2))
        return 0

    all_rows: List[Dict[str, Any]] = []
    grand = {"files": 0, "messages": 0, "ok": 0, "errors": 0}

    for f in files:
        rows, summary = qa_one_file(
            f,
            rules=rules,
            forced_profile=None,                     # use rules to resolve automatically
            quiet_parse=args.quiet_parse,
            cli_fail_on_dtm=True if args.fail_on_dtm else None,
        )
        all_rows.extend(rows)
        grand["files"] += 1
        grand["messages"] += summary["total"]
        grand["ok"] += summary["ok"]
        grand["errors"] += summary["errors"]

        print(f"[file] {f.name} → messages: {summary['total']}  ok: {summary['ok']}  errors: {summary['errors']}")
        limit = len(rows) if args.verbose else min(args.max_print, len(rows))
        for r in rows[:limit]:
            print(f"  [{r['status']}] msg#{r['message_index']} type={r.get('msg_type','')}^{r.get('msg_event','')}".rstrip("^"))
            if r.get("error"):
                print(f"    error: {r['error']}")
            if r.get("issues"):
                print(f"    issues: {', '.join(r['issues'])}")
            if r.get("dtm_issues"):
                print(f"    dtm_issues: {', '.join(r['dtm_issues'])}")
            if r.get("domain_issues"):
                print(f"    domain_issues: {', '.join(r['domain_issues'])}")
            if r.get("obx_issues"):
                print(f"    obx_issues: {', '.join(r['obx_issues'])}")
            print(f"    OBR-24: {r.get('obr24_values','')}   OBR-25: {r.get('obr25_values','')}   OBX-11: {r.get('obx11_values','')}")
            if r.get("txa2_id") or r.get("txa2_system"):
                print(f"    TXA-2: id={r.get('txa2_id','')} text={r.get('txa2_text','')} system={r.get('txa2_system','')} (2.3.2={r.get('txa2_3_2','')})")
            print(f"    MSH-10: {r.get('msh_10','')}   PID-3: {r.get('pid_3','')}")
            print(f"    counts: OBR={r.get('obr_count',0)} OBX={r.get('obx_count',0)}")

    # CSV output
    if args.report:
        csv_path = Path(args.report)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        root_for_output = target if target.is_dir() else target.parent
        csv_path = root_for_output / "hl7_qa_report.csv"
    write_csv(csv_path, all_rows)

    if args.as_json:
        print(json.dumps(all_rows, ensure_ascii=False))

    print(f"\n[total] files: {grand['files']}  messages: {grand['messages']}  ok: {grand['ok']}  errors: {grand['errors']}")
    print(f"[report] {csv_path}")
    return 0 if grand["errors"] == 0 else 1

def main(argv: List[str]) -> int:
    return run_cli(argv)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
