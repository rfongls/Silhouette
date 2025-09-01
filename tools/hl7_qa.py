#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HL7 QA: rules-aware, per-message validator (profiles + policies)

- Engines:
    * fast   — raw ER7 parsing (no object tree) for HL7Spy-like speed (default via rules)
    * hl7apy — full object parse when you need grammar/group reasoning
  Choose per-profile in rules.yaml (profile.engine) or override with --engine.

- Robust message splitting (handles BOMs/UTF-16/HLLP/MLLP; newline-agnostic; any FS after 'MSH')
- Large I/O buffers
- CSV or JSONL reporting
- Progress, start/limit, message-type filtering
- Optional parallel execution (process pool)
- hl7apy controls:
    * --hl7apy-validation {none|tolerant|strict}  (default: none)
    * --no-quiet-parse to show hl7apy logs/warnings (default: suppressed)

Timestamp policy (rules.yaml → timestamps.mode):
  - length_only (default) — accept if base digits match allowed lengths (8/12/14)
  - calendar              — additionally check real calendar ranges
  - off                   — skip TS checks

Report behavior:
  - CSV defaults to **per-issue rows** with columns:
      index,msg_ctrl_id,msg_type,version,field,value_received,validation_value,issue_type,issue
    Use --report-mode per-message to aggregate back into one row per message.
  - Default output path (when --report is omitted): <repo root>/tests/artifacts/hl7/<input_stem>_<engine>.csv
    Override with --report-dir or env HL7_QA_REPORT_DIR; explicit --report always wins.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import re
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import cpu_count
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------- Optional: PyYAML for rules ----------
try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

# ---------- hl7apy (optional, only used if engine=hl7apy) ----------
try:
    from hl7apy.core import Message, Segment  # noqa: F401  (for type hints / runtime when installed)
    from hl7apy.exceptions import HL7apyException
    HL7APY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    HL7APY_AVAILABLE = False


# =======================================================================
# Robust message splitting + normalization + I/O utils
# =======================================================================

UTF8_BOM = b"\xef\xbb\xbf"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"

# Start of buffer (\A) OR immediately after \r or \n, then 'MSH' and any FS byte.
MSH_START_RE = re.compile(br'(?:(?<=\r)|(?<=\n)|\A)MSH.', re.I)

def _normalize_blob(blob: bytes) -> bytes:
    if blob.startswith(UTF8_BOM):
        blob = blob[len(UTF8_BOM):]
    if blob.startswith(UTF16_LE_BOM):
        blob = blob.decode("utf-16-le", errors="ignore").encode("utf-8", errors="ignore")
    elif blob.startswith(UTF16_BE_BOM):
        blob = blob.decode("utf-16-be", errors="ignore").encode("utf-8", errors="ignore")
    blob = blob.replace(b"\r\n", b"\r").replace(b"\n", b"\r")
    for ch in (b"\x00", b"\x0b", b"\x1c", b"\x1d", b"\x1e"):
        blob = blob.replace(ch, b"")
    return blob

def fast_split_messages(blob: bytes) -> List[bytes]:
    blob = _normalize_blob(blob)
    starts = [m.start() for m in MSH_START_RE.finditer(blob)]
    if not starts:
        return []
    starts.append(len(blob))
    return [blob[starts[i]:starts[i+1]] for i in range(len(starts)-1)]

def read_file_bytes(path: str | Path) -> bytes:
    with open(path, "rb", buffering=1024 * 1024) as fh:
        return fh.read()

def ensure_text(b: bytes) -> str:
    return b.decode("utf-8", errors="ignore")

def _detect_fs_and_encs(first_line: str) -> Tuple[str, str, str, str]:
    fs = first_line[3:4] if len(first_line) >= 4 else "|"
    encs = first_line[4:8] if len(first_line) >= 8 else "^~\\&"
    comp = encs[0:1] if len(encs) >= 1 else "^"
    rep  = encs[1:2] if len(encs) >= 2 else "~"
    esc  = encs[2:3] if len(encs) >= 3 else "\\"
    sub  = encs[3:4] if len(encs) >= 4 else "&"
    return fs, comp, rep, sub

def msh_fields_from_raw(raw: bytes) -> Dict[str, str]:
    text = ensure_text(raw)
    first_line = text.split("\r", 1)[0]
    fs, comp, rep, sub = _detect_fs_and_encs(first_line)
    parts = first_line.split(fs)
    def get(i: int) -> str:
        return parts[i] if len(parts) > i else ""
    msg_type_raw = get(8)
    msg_type_norm = msg_type_raw.replace("^", "_")
    msg_root = msg_type_raw.split("^")[0] if msg_type_raw else ""
    return {
        "msg_type_raw": msg_type_raw,
        "msg_type": msg_type_norm,
        "msg_root": msg_root,
        "msg_ctrl_id": get(9),
        "version": get(11),
    }


# =======================================================================
# hl7apy quiet + validation control
# =======================================================================

try:
    from hl7apy.consts import VALIDATION_LEVEL as _VL  # STRICT / TOLERANT / NO_VALIDATION (or QUIET)
except Exception:
    _VL = None

def _map_validation_level(name: str):
    name = (name or "").lower()
    if not _VL:
        return None
    if name in ("none", "off", "ignore", "disabled"):
        return getattr(_VL, "NO_VALIDATION", None) or getattr(_VL, "QUIET", None) or getattr(_VL, "TOLERANT", None)
    if name in ("tolerant", "relaxed"):
        return getattr(_VL, "TOLERANT", None) or getattr(_VL, "QUIET", None)
    if name == "strict":
        return getattr(_VL, "STRICT", None)
    return None

def configure_hl7apy_logging(quiet: bool = True) -> None:
    names = ("hl7apy", "hl7apy.core", "hl7apy.parser", "hl7apy.base", "hl7apy.validators")
    for n in names:
        lg = logging.getLogger(n)
        lg.handlers = []
        lg.propagate = False
        if quiet:
            lg.addHandler(logging.NullHandler())
            lg.setLevel(logging.CRITICAL)
        else:
            if not lg.handlers:
                logging.basicConfig()
            lg.setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", module="hl7apy")

@contextmanager
def suppress_hl7apy_output(enabled: bool = True):
    if not enabled:
        yield; return
    with open(os.devnull, "w") as devnull, redirect_stderr(devnull), redirect_stdout(devnull):
        yield

def parse_hl7(text: str, *, quiet: bool = True, validation: str = "none"):
    lvl = _map_validation_level(validation)
    from hl7apy.parser import parse_message as _parse_message
    with suppress_hl7apy_output(quiet):
        if lvl is not None:
            return _parse_message(text, find_groups=False, validation_level=lvl)
        return _parse_message(text, find_groups=False)


# =======================================================================
# Rules model (profiles, policies, allowed values)
# =======================================================================

_TS_BASE_ALLOWED_DEFAULT = {4, 6, 8, 10, 12, 14}
_TS_FRACTZ = re.compile(r'^(?:\.(\d{1,4}))?(Z|[+\-]\d{4})?$')

DEFAULT_TS_FIELDS = [
    "MSH-7","EVN-2","EVN-6","PID-7","PV1-44","PV2-8",
    "OBR-6","OBR-7","OBR-8","OBR-14","OBR-22","OBX-14","TXA-6"
]

@dataclass
class TimestampRuleConfig:
    strict: bool = True
    fail_on_dtm: bool = True
    allowed_lengths: set[int] = field(default_factory=lambda: set(_TS_BASE_ALLOWED_DEFAULT))
    compliant_lengths: set[int] = field(default_factory=lambda: set(_TS_BASE_ALLOWED_DEFAULT))
    fields: List[str] = field(default_factory=list)
    mode: str = "length_only"  # 'length_only' | 'calendar' | 'off'

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "TimestampRuleConfig":
        return TimestampRuleConfig(
            strict=bool(d.get("strict", True)),
            fail_on_dtm=bool(d.get("fail_on_dtm", True)),
            allowed_lengths=set(int(x) for x in d.get("allowed_lengths", list(_TS_BASE_ALLOWED_DEFAULT))),
            compliant_lengths=set(int(x) for x in d.get("compliant_lengths", list(_TS_BASE_ALLOWED_DEFAULT))),
            fields=list(d.get("fields", [])),
            mode=str(d.get("mode", "length_only")).lower(),
        )

@dataclass
class AllowedValuesConfig:
    obr24: List[str] = field(default_factory=list)
    result_status: List[str] = field(default_factory=list)
    obx11_empty_allows: List[str] = field(default_factory=list)
    encounter_class: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AllowedValuesConfig":
        return AllowedValuesConfig(
            obr24=list(d.get("obr24", [])),
            result_status=list(d.get("result_status", [])),
            obx11_empty_allows=list(d.get("obx11_empty_allows", [])),
            encounter_class=list(d.get("encounter_class", [])),
        )

@dataclass
class PoliciesConfig:
    require_pid3_shape: bool = False
    require_obr2_or_obr3: bool = False
    obr4_coded: bool = False
    obr25_allowed: bool = False
    obx11_allowed: bool = False
    obx3_coded: bool = False
    obx5_required_unless_status_in_empty_allows: bool = False
    obx2_vs_obx5_typecheck: bool = False
    txa2_coded: bool = False
    require_pv1_2_encounter_class: bool = False
    required_fields: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PoliciesConfig":
        return PoliciesConfig(
            require_pid3_shape=bool(d.get("require_pid3_shape", False)),
            require_obr2_or_obr3=bool(d.get("require_obr2_or_obr3", False)),
            obr4_coded=bool(d.get("obr4_coded", False)),
            obr25_allowed=bool(d.get("obr25_allowed", False)),
            obx11_allowed=bool(d.get("obx11_allowed", False)),
            obx3_coded=bool(d.get("obx3_coded", False)),
            obx5_required_unless_status_in_empty_allows=bool(d.get("obx5_required_unless_status_in_empty_allows", False)),
            obx2_vs_obx5_typecheck=bool(d.get("obx2_vs_obx5_typecheck", False)),
            txa2_coded=bool(d.get("txa2_coded", False)),
            require_pv1_2_encounter_class=bool(d.get("require_pv1_2_encounter_class", False)),
            required_fields=list(d.get("required_fields", [])),
        )

@dataclass
class Profile:
    name: str
    types: List[str] = field(default_factory=list)  # ORU, ADT, ...
    engine: Optional[str] = None                   # "fast" | "hl7apy"
    timestamps: Optional[TimestampRuleConfig] = None
    allowed: AllowedValuesConfig = field(default_factory=AllowedValuesConfig)
    policies: PoliciesConfig = field(default_factory=PoliciesConfig)

    @staticmethod
    def from_dict(name: str, d: Dict[str, Any]) -> "Profile":
        ts = d.get("timestamps")
        return Profile(
            name=name,
            types=list(d.get("types", [])),
            engine=d.get("engine"),
            timestamps=TimestampRuleConfig.from_dict(ts) if ts else None,
            allowed=AllowedValuesConfig.from_dict(d.get("allowed", {})),
            policies=PoliciesConfig.from_dict(d.get("policies", {})),
        )

@dataclass
class RuleSet:
    profiles: Dict[str, Profile] = field(default_factory=dict)
    default_profile: Optional[str] = None

    @staticmethod
    def load(path: Optional[str | Path]) -> "RuleSet":
        if not path:
            return RuleSet()
        if yaml is None:
            raise RuntimeError("PyYAML not installed; cannot load rules")
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        profiles = {}
        for name, pd in (data.get("profiles") or {}).items():
            profiles[name] = Profile.from_dict(name, pd or {})
        default_profile = data.get("default_profile")
        return RuleSet(profiles=profiles, default_profile=default_profile)

    def select_profile_for_root(self, msg_root: str) -> Optional[Profile]:
        for p in self.profiles.values():
            if msg_root and msg_root in p.types:
                return p
        if self.default_profile and self.default_profile in self.profiles:
            return self.profiles[self.default_profile]
        return None

    def to_dict(self) -> Dict[str, Any]:
        out = {"default_profile": self.default_profile, "profiles": {}}
        for name, p in self.profiles.items():
            out["profiles"][name] = {
                "types": p.types,
                "engine": p.engine,
                "timestamps": None if not p.timestamps else {
                    "strict": p.timestamps.strict,
                    "fail_on_dtm": p.timestamps.fail_on_dtm,
                    "allowed_lengths": sorted(p.timestamps.allowed_lengths),
                    "compliant_lengths": sorted(p.timestamps.compliant_lengths),
                    "fields": p.timestamps.fields,
                    "mode": p.timestamps.mode,
                },
                "allowed": {
                    "obr24": p.allowed.obr24,
                    "result_status": p.allowed.result_status,
                    "obx11_empty_allows": p.allowed.obx11_empty_allows,
                    "encounter_class": p.allowed.encounter_class,
                },
                "policies": {
                    "require_pid3_shape": p.policies.require_pid3_shape,
                    "require_obr2_or_obr3": p.policies.require_obr2_or_obr3,
                    "obr4_coded": p.policies.obr4_coded,
                    "obr25_allowed": p.policies.obr25_allowed,
                    "obx11_allowed": p.policies.obx11_allowed,
                    "obx3_coded": p.policies.obx3_coded,
                    "obx5_required_unless_status_in_empty_allows": p.policies.obx5_required_unless_status_in_empty_allows,
                    "obx2_vs_obx5_typecheck": p.policies.obx2_vs_obx5_typecheck,
                    "txa2_coded": p.policies.txa2_coded,
                    "require_pv1_2_encounter_class": p.policies.require_pv1_2_encounter_class,
                    "required_fields": p.policies.required_fields,
                }
            }
        return out

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RuleSet":
        profiles = {}
        for name, pd in (d.get("profiles") or {}).items():
            profiles[name] = Profile.from_dict(name, pd or {})
        return RuleSet(profiles=profiles, default_profile=d.get("default_profile"))


# =======================================================================
# Field extraction (raw and hl7apy) + fast ER7 index
# =======================================================================

_FIELD_SPEC_RE = re.compile(r'^([A-Z0-9]{3})-(\d+)(?:\.(\d+))?(?:\.(\d+))?$')

def parse_field_spec(spec: str) -> Tuple[str, int, Optional[int], Optional[int]]:
    m = _FIELD_SPEC_RE.match(spec.strip())
    if not m:
        raise ValueError(f"Invalid field spec: {spec}")
    seg = m.group(1)
    fld = int(m.group(2))
    comp = int(m.group(3)) if m.group(3) else None
    sub = int(m.group(4)) if m.group(4) else None
    return seg, fld, comp, sub

def values_from_parsed(msg: "Message", spec: str) -> List[str]:
    seg, fld, comp, sub = parse_field_spec(spec)
    out: List[str] = []
    try:
        segs: List["Segment"] = list(msg.segments(seg))  # type: ignore[attr-defined]
        for s in segs:
            try:
                field_obj = s[fld]
            except Exception:
                continue
            reps = field_obj if isinstance(field_obj, list) else [field_obj]
            for rep in reps:
                try:
                    val = rep
                    if comp is not None:
                        val = rep[comp]
                    if sub is not None:
                        val = val[sub]
                    v = getattr(val, "value", None)
                    out.append(str(v if v is not None else val))
                except Exception:
                    try:
                        out.append(str(rep.value))
                    except Exception:
                        pass
    except Exception:
        pass
    return [v.strip() for v in out if str(v).strip()]

# ---------- FIXED: correct MSH indexing in raw path ----------
def values_from_raw(raw: bytes, spec: str) -> List[str]:
    text = ensure_text(raw)
    lines = text.split("\r")
    if not lines:
        return []
    fs, comp, rep, sub = _detect_fs_and_encs(lines[0])
    seg, fld, comp_i, sub_i = parse_field_spec(spec)
    out: List[str] = []
    for ln in lines:
        if not ln.startswith(seg + fs):
            continue
        fields = ln.split(fs)
        # SPECIAL: MSH has off-by-one indexing because MSH-1 is the separator itself
        if seg == "MSH":
            if fld == 1:
                fval = fs
            else:
                pos = fld - 1
                if len(fields) <= pos:
                    continue
                fval = fields[pos]
        else:
            if len(fields) <= fld:
                continue
            fval = fields[fld]
        # Handle repetitions/components/subcomponents
        for f_rep in fval.split(rep):
            if comp_i is None:
                out.append(f_rep)
            else:
                comps = f_rep.split(comp)
                if len(comps) >= comp_i:
                    cval = comps[comp_i - 1]
                    if sub_i is None:
                        out.append(cval)
                    else:
                        subs = cval.split(sub)
                        if len(subs) >= sub_i:
                            out.append(subs[sub_i - 1])
    return [v.strip() for v in out if v.strip()]

# ---------- (RE)ADDED: build the fast ER7 index ----------
def build_msg_index(raw: bytes) -> Tuple[Dict[str, List[List[str]]], str, str, str, str]:
    """
    Return (index, fs, comp, rep, sub)
    index: { 'SEG': [ fields_list_per_segment_instance ] }
    """
    text = ensure_text(raw)
    lines = text.split("\r")
    if not lines or not lines[0].startswith("MSH"):
        return {}, "|", "^", "~", "&"
    fs, comp, rep, sub = _detect_fs_and_encs(lines[0])
    idx: Dict[str, List[List[str]]] = {}
    for ln in lines:
        if len(ln) < 4 or ln[3:4] != fs:
            continue
        seg = ln[0:3]
        if not seg or not seg.isalnum() or not seg[0].isupper():
            continue
        fields = ln.split(fs)
        idx.setdefault(seg, []).append(fields)
    return idx, fs, comp, rep, sub

# ---------- FIXED: correct MSH indexing in indexed path ----------
def values_from_index(idx: Dict[str, List[List[str]]],
                      fs: str, comp: str, rep: str, sub: str,
                      spec: str) -> List[str]:
    seg, fld, comp_i, sub_i = parse_field_spec(spec)
    out: List[str] = []
    for fields in idx.get(seg, []):
        # SPECIAL: MSH has off-by-one indexing because MSH-1 is the separator itself
        if seg == "MSH":
            if fld == 1:
                fval = fs
            else:
                pos = fld - 1
                if len(fields) <= pos:
                    continue
                fval = fields[pos]
        else:
            if len(fields) <= fld:
                continue
            fval = fields[fld]
        for f_rep in fval.split(rep):
            if comp_i is None:
                out.append(f_rep)
            else:
                comps = f_rep.split(comp)
                if len(comps) >= comp_i:
                    cval = comps[comp_i - 1]
                    if sub_i is None:
                        out.append(cval)
                    else:
                        subs = cval.split(sub)
                        if len(subs) >= sub_i:
                            out.append(subs[sub_i - 1])
    return [v.strip() for v in out if v.strip()]

def get_values(spec: str,
               engine: str,
               raw: bytes,
               idx_pack: Optional[Tuple[Dict[str, List[List[str]]], str, str, str, str]] = None,
               parsed: Optional["Message"] = None) -> List[str]:
    """
    Unified accessor so rule logic doesn't care which engine is in use.
    'fast' uses the ER7 index; 'hl7apy' uses parsed tree with raw fallback.
    """
    if engine == "fast":
        if idx_pack is None:
            idx_pack = build_msg_index(raw)
        idx, fs, comp, rep, sub = idx_pack
        return values_from_index(idx, fs, comp, rep, sub, spec)
    else:
        vals: List[str] = []
        if parsed is not None:
            vals = values_from_parsed(parsed, spec)
        if not vals:
            vals = values_from_raw(raw, spec)
        return vals


# =======================================================================
# Validation helpers (TS)
# =======================================================================

NUMERIC_RE = re.compile(r'^[+-]?(\d+(\.\d+)?|\.\d+)$')

def _slice_ts_base(ts: str) -> Tuple[str, str]:
    m = re.match(r'^(\d{4,14})(.*)$', ts)
    if not m:
        return "", ""
    return m.group(1), m.group(2)

def ts_length_ok(ts: str, allowed: set[int]) -> Tuple[bool, str]:
    base, rest = _slice_ts_base(ts)
    if not base:
        return False, "bad format"
    if len(base) not in allowed:
        return False, f"length {len(base)} not allowed"
    if rest and not _TS_FRACTZ.match(rest):
        return False, "invalid fraction/timezone"
    return True, ""

def ts_calendar_ok(ts: str) -> Tuple[bool, str]:
    base, _rest = _slice_ts_base(ts)
    if not base:
        return False, "bad format"
    try:
        y = int(base[0:4])
        if len(base) == 4:
            return True, ""
        m = int(base[4:6]);  assert 1 <= m <= 12
        if len(base) == 6:
            return True, ""
        d = int(base[6:8]);  datetime(y, m, d)
        if len(base) == 8:
            return True, ""
        H = int(base[8:10]); assert 0 <= H <= 23
        if len(base) == 10:
            datetime(y, m, d, H, 0, 0); return True, ""
        M = int(base[10:12]); assert 0 <= M <= 59
        if len(base) == 12:
            datetime(y, m, d, H, M, 0); return True, ""
        S = int(base[12:14]); assert 0 <= S <= 59
        datetime(y, m, d, H, M, S); return True, ""
    except Exception as e:
        return False, f"invalid date/time: {e}"


# =======================================================================
# Issue container (now structured)
# =======================================================================

@dataclass
class IssueItem:
    kind: str                 # "error" | "warning"
    message: str
    spec: Optional[str] = None
    value: Optional[str] = None
    expected: Optional[str] = None

@dataclass
class IssueSet:
    errors: List[str] = field(default_factory=list)     # legacy prints
    warnings: List[str] = field(default_factory=list)   # legacy prints
    items: List[IssueItem] = field(default_factory=list)

    def add_issue(self, kind: str, message: str, cap: int,
                  spec: Optional[str] = None,
                  value: Optional[str] = None,
                  expected: Optional[str] = None):
        # Maintain legacy lists (respect cap)
        target = self.errors if kind == "error" else self.warnings
        if len(target) < cap:
            target.append(message)
            self.items.append(IssueItem(kind=kind, message=message, spec=spec, value=value, expected=expected))
        elif len(target) == cap:
            target.append(f"... truncated at {cap} {kind}s")

    def add_err(self, msg: str, cap: int, **meta):
        self.add_issue("error", msg, cap, **meta)

    def add_warn(self, msg: str, **meta):
        self.warnings.append(msg)
        self.items.append(IssueItem(kind="warning", message=msg, **meta))


# =======================================================================
# Message validation (per profile)
# =======================================================================

@dataclass
class ValidationContext:
    quiet_parse: bool
    hl7apy_validation: str
    engine_pref: str  # "auto" | "fast" | "hl7apy"

def validate_message(
    raw: bytes,
    rules: RuleSet,
    max_errors_per_msg: int,
    ctx: ValidationContext,
) -> Tuple[Dict[str, str], IssueSet]:
    hdr = msh_fields_from_raw(raw)
    issues = IssueSet()

    profile = rules.select_profile_for_root(hdr.get("msg_root", ""))
    if profile is None:
        return {"msg_type": hdr["msg_type"], "msg_ctrl_id": hdr["msg_ctrl_id"], "version": hdr["version"]}, issues

    engine_eff = ctx.engine_pref if ctx.engine_pref != "auto" else (profile.engine or "fast")

    idx_pack = build_msg_index(raw)
    parsed: Optional["Message"] = None
    if engine_eff == "hl7apy":
        if not HL7APY_AVAILABLE:
            issues.add_err("hl7apy not installed; cannot use hl7apy engine", max_errors_per_msg)
        else:
            with suppress_hl7apy_output(ctx.quiet_parse):
                try:
                    parsed = parse_hl7(ensure_text(raw), quiet=ctx.quiet_parse, validation=ctx.hl7apy_validation)
                except HL7apyException as e:
                    issues.add_err(f"parse_error: {e}", max_errors_per_msg)

    # ---------------- Timestamps ----------------
    if profile.timestamps and profile.timestamps.mode != "off":
        ts_cfg = profile.timestamps
        ts_fields = ts_cfg.fields if ts_cfg.fields else list(DEFAULT_TS_FIELDS)
        allowed_str = f"allowed lengths: {sorted(ts_cfg.allowed_lengths)}"
        compliant_str = f"compliant lengths: {sorted(ts_cfg.allowed_lengths)}"
        for spec in ts_fields:
            for v in get_values(spec, engine_eff, raw, idx_pack, parsed):
                if not v:
                    continue
                ok_len, why_len = ts_length_ok(v, ts_cfg.allowed_lengths)
                if not ok_len:
                    issues.add_err(
                        f"{spec} invalid TS '{v}': {why_len}",
                        max_errors_per_msg,
                        spec=spec, value=v, expected=allowed_str
                    )
                    continue
                if ts_cfg.mode == "calendar":
                    ok_cal, why_cal = ts_calendar_ok(v)
                    if not ok_cal:
                        issues.add_err(
                            f"{spec} invalid TS '{v}': {why_cal}",
                            max_errors_per_msg,
                            spec=spec, value=v, expected="calendar-valid date/time"
                        )
                m = re.match(r'^(\d{4,14})', v)
                base_len = len(m.group(1)) if m else len(v)
                if base_len not in ts_cfg.compliant_lengths:
                    issues.add_warn(
                        f"{spec} TS length {base_len} accepted but non-compliant",
                        spec=spec, value=v, expected=compliant_str
                    )

    # ---------------- Policies & allowed values ----------------
    pol = profile.policies
    allowed = profile.allowed

    if pol.required_fields:
        for spec in pol.required_fields:
            if not any(get_values(spec, engine_eff, raw, idx_pack, parsed)):
                issues.add_err(f"{spec} required but missing/empty",
                               max_errors_per_msg, spec=spec, value="", expected="non-empty")

    if pol.require_pid3_shape:
        ok_shape = (any(get_values("PID-3.1", engine_eff, raw, idx_pack, parsed)) and
                    (any(get_values("PID-3.4", engine_eff, raw, idx_pack, parsed)) or
                     any(get_values("PID-3.5", engine_eff, raw, idx_pack, parsed))))
        if not ok_shape:
            issues.add_err("PID-3 shape invalid: require .1 and (.4 or .5)",
                           max_errors_per_msg, spec="PID-3", expected="PID-3.1 and (PID-3.4 or PID-3.5)")

    if pol.require_obr2_or_obr3:
        has2 = any(get_values("OBR-2.1", engine_eff, raw, idx_pack, parsed))
        has3 = any(get_values("OBR-3.1", engine_eff, raw, idx_pack, parsed))
        if not (has2 or has3):
            issues.add_err("OBR requires at least one of OBR-2 (placer) or OBR-3 (filler)",
                           max_errors_per_msg, spec="OBR-2|OBR-3", expected="OBR-2.1 or OBR-3.1 present")

    if pol.obr4_coded:
        has41 = any(get_values("OBR-4.1", engine_eff, raw, idx_pack, parsed))
        has43 = any(get_values("OBR-4.3", engine_eff, raw, idx_pack, parsed))
        if not (has41 and has43):
            issues.add_err("OBR-4 must be coded (requires .1 id and .3 system)",
                           max_errors_per_msg, spec="OBR-4", expected="OBR-4.1 and OBR-4.3 present")

    if pol.obr25_allowed and allowed.result_status:
        for v in get_values("OBR-25", engine_eff, raw, idx_pack, parsed):
            if v and v not in allowed.result_status:
                issues.add_err(f"OBR-25 result_status '{v}' not allowed",
                               max_errors_per_msg, spec="OBR-25", value=v,
                               expected=f"allowed: {allowed.result_status}")

    if allowed.obr24:
        for v in get_values("OBR-24", engine_eff, raw, idx_pack, parsed):
            if v and v not in allowed.obr24:
                issues.add_err(f"OBR-24 specimen_action_code '{v}' not in allowed list",
                               max_errors_per_msg, spec="OBR-24", value=v,
                               expected=f"allowed: {allowed.obr24}")

    if pol.obx11_allowed and allowed.result_status:
        for v in get_values("OBX-11", engine_eff, raw, idx_pack, parsed):
            if v and v not in allowed.result_status:
                issues.add_err(f"OBX-11 result_status '{v}' not allowed",
                               max_errors_per_msg, spec="OBX-11", value=v,
                               expected=f"allowed: {allowed.result_status}")

    if pol.obx5_required_unless_status_in_empty_allows:
        obx11 = get_values("OBX-11", engine_eff, raw, idx_pack, parsed)
        obx5  = get_values("OBX-5.1", engine_eff, raw, idx_pack, parsed) or \
                get_values("OBX-5",   engine_eff, raw, idx_pack, parsed)
        if any(v and v not in allowed.obx11_empty_allows for v in obx11) and not any(obx5):
            issues.add_err("OBX-5 required unless OBX-11 in empty-allows",
                           max_errors_per_msg, spec="OBX-5",
                           expected=f"required unless OBX-11 ∈ {allowed.obx11_empty_allows}")

    if pol.obx3_coded:
        has31 = any(get_values("OBX-3.1", engine_eff, raw, idx_pack, parsed))
        has33 = any(get_values("OBX-3.3", engine_eff, raw, idx_pack, parsed))
        if not (has31 and has33):
            issues.add_err("OBX-3 must be coded (requires .1 id and .3 system)",
                           max_errors_per_msg, spec="OBX-3", expected="OBX-3.1 and OBX-3.3 present")

    if pol.obx2_vs_obx5_typecheck:
        for t in (v.strip().upper() for v in get_values("OBX-2", engine_eff, raw, idx_pack, parsed)):
            if not t:
                continue
            obx5_val = next(iter(get_values("OBX-5", engine_eff, raw, idx_pack, parsed)), "")
            if t == "NM":
                if not obx5_val or not NUMERIC_RE.match(obx5_val):
                    issues.add_err("OBX-2=NM requires OBX-5 numeric",
                                   max_errors_per_msg, spec="OBX-5", value=obx5_val, expected="numeric")
            elif t in ("TS","DT","DTM"):
                ok_len, why_len = ts_length_ok(obx5_val, profile.timestamps.allowed_lengths if profile.timestamps else _TS_BASE_ALLOWED_DEFAULT)
                if not ok_len:
                    issues.add_err(f"OBX-2={t} requires OBX-5 TS-valid: '{obx5_val}' ({why_len})",
                                   max_errors_per_msg, spec="OBX-5", value=obx5_val,
                                   expected=f"TS {sorted(profile.timestamps.allowed_lengths if profile.timestamps else _TS_BASE_ALLOWED_DEFAULT)}")
            elif t in ("CE","CWE"):
                if not any(get_values("OBX-5.1", engine_eff, raw, idx_pack, parsed)):
                    issues.add_err("OBX-2=CE/CWE requires OBX-5.1 coded id",
                                   max_errors_per_msg, spec="OBX-5.1", expected="coded id present")

    if pol.txa2_coded:
        has21 = any(get_values("TXA-2.1", engine_eff, raw, idx_pack, parsed))
        has23 = any(get_values("TXA-2.3", engine_eff, raw, idx_pack, parsed))
        if not (has21 and has23):
            issues.add_err("TXA-2 must be coded (requires .1 id and .3 system)",
                           max_errors_per_msg, spec="TXA-2", expected="TXA-2.1 and TXA-2.3 present")

    if pol.require_pv1_2_encounter_class:
        pv1_2_vals = get_values("PV1-2", engine_eff, raw, idx_pack, parsed)
        if not any(pv1_2_vals):
            issues.add_err("PV1-2 (encounter/patient class) required but missing/empty",
                           max_errors_per_msg, spec="PV1-2", expected="non-empty")
        elif allowed.encounter_class:
            for v in pv1_2_vals:
                if v and v not in allowed.encounter_class:
                    issues.add_err(f"PV1-2 encounter class '{v}' not in allowed set",
                                   max_errors_per_msg, spec="PV1-2", value=v,
                                   expected=f"allowed: {allowed.encounter_class}")

    return {"msg_type": hdr["msg_type"], "msg_ctrl_id": hdr["msg_ctrl_id"], "version": hdr["version"]}, issues


# =======================================================================
# Parallel worker
# =======================================================================

def _worker_validate_chunk(
    chunk: List[bytes],
    rules_dict: Dict[str, Any],
    max_errors_per_msg: int,
    ctx: ValidationContext,
) -> List[Tuple[Dict[str, str], IssueSet]]:
    configure_hl7apy_logging(quiet=ctx.quiet_parse)
    rules = RuleSet.from_dict(rules_dict)
    out: List[Tuple[Dict[str, str], IssueSet]] = []
    for raw in chunk:
        head, iss = validate_message(raw, rules, max_errors_per_msg=max_errors_per_msg, ctx=ctx)
        out.append((head, iss))
    return out


# =======================================================================
# Reporting (defaults + robust writers)
# =======================================================================

def _default_report_dir(_cwd: Path) -> Path:
    """Always default to <repo root>/tests/artifacts/hl7."""
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "tests" / "artifacts" / "hl7"

def resolve_report_path(report: Optional[str], input_file: str, engine_name: str, report_dir: Optional[str] = None) -> Path:
    if report:
        p = Path(report)
        if p.suffix.lower() not in (".csv", ".jsonl", ""):
            p = p.with_suffix(".csv")
        return p
    base_dir = Path(report_dir) if report_dir else None
    if base_dir is None:
        env_dir = os.getenv("HL7_QA_REPORT_DIR")
        base_dir = Path(env_dir) if env_dir else None
    if base_dir is None:
        base_dir = _default_report_dir(Path.cwd())
    base_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(input_file).stem or "report"
    return base_dir / f"{stem}_{engine_name}.csv"

def open_csv_writer(path: str | Path, mode: str = "per-issue") -> Tuple[io.TextIOBase, csv.writer]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = p.open("w", newline="", encoding="utf-8", buffering=1024 * 1024)
    w = csv.writer(fh)
    if mode == "per-message":
        w.writerow(["index", "msg_ctrl_id", "msg_type", "version", "errors", "warnings"])
    else:
        w.writerow(["index", "msg_ctrl_id", "msg_type", "version", "field", "value_received", "validation_value", "issue_type", "issue"])
    return fh, w

def open_jsonl_writer(path: str | Path) -> io.TextIOBase:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    return p.open("w", encoding="utf-8", buffering=1024 * 1024)

def write_csv_row_per_message(writer: csv.writer, idx: int, header: Dict[str, str], issues: IssueSet) -> None:
    writer.writerow([idx, header.get("msg_ctrl_id",""), header.get("msg_type",""),
                     header.get("version",""), "; ".join(issues.errors), "; ".join(issues.warnings)])

def write_csv_rows_per_issue(writer: csv.writer, idx: int, header: Dict[str, str], issues: IssueSet) -> None:
    base = [idx, header.get("msg_ctrl_id", ""), header.get("msg_type", ""), header.get("version", "")]
    for it in issues.items:
        if it.message.startswith("... "):  # skip truncation meta-lines
            continue
        writer.writerow(base + [it.spec or "", it.value or "", it.expected or "", it.kind, it.message])

def write_jsonl_row(fh: io.TextIOBase, idx: int, header: Dict[str, str], issues: IssueSet) -> None:
    fh.write(json.dumps({
        "index": idx,
        "msg_ctrl_id": header.get("msg_ctrl_id",""),
        "msg_type": header.get("msg_type",""),
        "version": header.get("version",""),
        "errors": issues.errors,
        "warnings": issues.warnings,
        "issues": [it.__dict__ for it in issues.items],
    }, ensure_ascii=False) + "\n")


# =======================================================================
# CLI
# =======================================================================

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HL7 QA: rules-aware per-message validator (profiles)")
    p.add_argument("input", help="Path to HL7 file")
    p.add_argument("--rules", help="Path to YAML rules file", required=False)
    p.add_argument("--report", help="Output (.csv or .jsonl). If omitted, a default path is chosen.", required=False)
    p.add_argument("--report-dir", help="Directory for report when --report is omitted (env HL7_QA_REPORT_DIR also supported).", required=False)
    p.add_argument("--report-mode", choices=["per-issue", "per-message"], default="per-issue",
                   help="CSV rows: 'per-issue' (default) or 'per-message' (aggregate).")
    p.add_argument("--progress-every", type=int, default=0)
    p.add_argument("--progress-time", type=float, default=0.0)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--only", help="Comma-separated message types (ORU_R01, ADT_A01, ...)")
    p.add_argument("--max-print", type=int, default=3)
    p.add_argument("--max-errors-per-msg", type=int, default=50)
    p.add_argument("--engine", choices=["auto", "fast", "hl7apy"], default="auto",
                   help="Engine: 'auto' (use profile.engine or fast), 'fast', 'hl7apy'.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--light-parse", action="store_true", help="Alias for --engine fast")
    g.add_argument("--full-parse", action="store_true", help="Alias for --engine hl7apy")
    p.add_argument("--no-quiet-parse", action="store_true", help="Show hl7apy logs (default: suppressed)")
    p.add_argument("--hl7apy-validation", choices=["none","tolerant","strict"], default="none")
    p.add_argument("--workers", default="0", help="'auto' or integer (0 = no parallel)")
    p.add_argument("--chunk", type=int, default=200)
    return p.parse_args(argv)


# =======================================================================
# Main
# =======================================================================

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    engine_pref = args.engine
    if args.light_parse:
        engine_pref = "fast"
    elif args.full_parse:
        engine_pref = "hl7apy"

    if engine_pref == "hl7apy" and not HL7APY_AVAILABLE:
        print("[error] hl7apy engine requested but hl7apy is not installed.", file=sys.stderr)
        return 2

    quiet_parse = not args.no_quiet_parse
    configure_hl7apy_logging(quiet=quiet_parse)
    hl7apy_validation = args.hl7apy_validation
    ctx = ValidationContext(quiet_parse=quiet_parse, hl7apy_validation=hl7apy_validation, engine_pref=engine_pref)

    blob = read_file_bytes(args.input)
    msgs = fast_split_messages(blob)
    total = len(msgs)
    if total == 0:
        print("[error] No messages found (no 'MSH' anchors).", file=sys.stderr)
        return 1

    start = max(0, int(args.start))
    end = total if args.limit <= 0 else min(total, start + int(args.limit))
    if start >= total:
        print(f"[error] --start={start} >= total messages ({total})", file=sys.stderr)
        return 1
    work_msgs = msgs[start:end]

    if args.rules:
        print(f"[rules] using: {Path(args.rules).resolve()}")
        rules = RuleSet.load(args.rules)
    else:
        rules = RuleSet()

    only_set: Optional[set[str]] = None
    if args.only:
        only_set = {x.strip() for x in args.only.split(",") if x.strip()}
        if only_set:
            filtered = []
            for raw in work_msgs:
                hdr = msh_fields_from_raw(raw)
                if hdr["msg_type"] in only_set or hdr["msg_type_raw"] in only_set:
                    filtered.append(raw)
            work_msgs = filtered

    writer_csv: Optional[csv.writer] = None
    fh_report: Optional[io.TextIOBase] = None
    write_row_fn = None

    engine_label = engine_pref
    report_path = resolve_report_path(args.report, args.input, engine_label, args.report_dir)

    ext = Path(report_path).suffix.lower()
    if not ext:
        report_path = report_path.with_suffix(".csv")
        ext = ".csv"

    if ext == ".csv":
        fh_report, writer_csv = open_csv_writer(report_path, mode=args.report_mode)
        if args.report_mode == "per-message":
            write_row_fn = lambda idx, header, issues: write_csv_row_per_message(writer_csv, idx, header, issues)
        else:
            write_row_fn = lambda idx, header, issues: write_csv_rows_per_issue(writer_csv, idx, header, issues)
    elif ext == ".jsonl":
        fh_report = open_jsonl_writer(report_path)
        write_row_fn = lambda idx, header, issues: write_jsonl_row(fh_report, idx, header, issues)
    else:
        print(f"[error] Unknown report extension '{ext}'. Use .csv or .jsonl", file=sys.stderr)
        return 2

    t0 = perf_counter()
    next_prog = int(args.progress_every) if args.progress_every else 0
    last_prog = t0
    n_proc = n_rows = 0
    tot_err = tot_warn = 0

    def maybe_progress(i: int):
        nonlocal last_prog
        now = perf_counter()
        by_count = (next_prog and (i % next_prog == 0))
        by_time = (args.progress_time and (now - last_prog) >= float(args.progress_time))
        if by_count or by_time:
            dt = now - t0
            rate = (i / dt) if dt else 0.0
            print(f"    [progress] {i} msgs  elapsed={dt:.1f}s  rate={rate:.1f} msg/s")
            last_prog = now

    # parallel?
    parallel = False
    max_workers = 0
    if isinstance(args.workers, str):
        w = args.workers.strip().lower()
        if w == "auto":
            max_workers = max(1, cpu_count()-1); parallel = True
        else:
            try:
                max_workers = int(w); parallel = max_workers > 0
            except Exception:
                parallel = False
    else:
        max_workers = int(args.workers); parallel = max_workers > 0

    if parallel:
        chunks: List[List[bytes]] = []
        ch = int(args.chunk) if int(args.chunk) > 0 else 200
        for i in range(0, len(work_msgs), ch):
            chunks.append(work_msgs[i:i+ch])
        rules_dict = rules.to_dict()
        collected: List[Tuple[Dict[str, str], IssueSet]] = []
        with ProcessPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(_worker_validate_chunk, c, rules_dict, int(args.max_errors_per_msg), ctx)
                    for c in chunks]
            done = 0
            for fut in as_completed(futs):
                res = fut.result()
                collected.extend(res)
                done += len(res)
                maybe_progress(done)
        results_iter = collected
    else:
        def gen():
            for i, raw in enumerate(work_msgs, 1):
                head, iss = validate_message(raw, rules, max_errors_per_msg=int(args.max_errors_per_msg), ctx=ctx)
                maybe_progress(i)
                yield head, iss
        results_iter = gen()

    for idx, (header, issues) in enumerate(results_iter, start=1 + start):
        n_proc += 1
        tot_err += len(issues.errors)
        tot_warn += len(issues.warnings)
        if args.max_print and (issues.errors or issues.warnings):
            printed = 0
            for e in issues.errors[:args.max_print]:
                print(f"[{idx}] ERR: {e}"); printed += 1
            if printed < args.max_print:
                for w in issues.warnings[:(args.max_print-printed)]:
                    print(f"[{idx}] WRN: {w}")
        if write_row_fn:
            write_row_fn(idx, header, issues); n_rows += 1

    if fh_report:
        fh_report.close()
        try:
            print(f"[report] wrote: {Path(report_path).resolve()}")
        except Exception:
            print(f"[report] wrote: {report_path}")

    dt = perf_counter() - t0
    rate = (n_proc / dt) if dt else 0.0
    print(f"[summary] msgs={n_proc} elapsed={dt:.1f}s rate={rate:.1f} msg/s errors={tot_err} warnings={tot_warn}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[abort] Interrupted by user", file=sys.stderr)
        sys.exit(130)
