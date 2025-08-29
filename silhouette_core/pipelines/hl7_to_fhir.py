"""Minimal HL7 v2 → FHIR translation pipeline."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import yaml

from translators import transforms
from translators.mapping_loader import load as load_map, MapSpec


def _parse_hl7(text: str) -> Dict[str, List[List[str]]]:
    data: Dict[str, List[List[str]]] = {}
    for line in text.strip().splitlines():
        fields = line.strip().split("|")
        if not fields:
            continue
        data.setdefault(fields[0], []).append(fields)
    return data


def _parse_token(token: str) -> tuple[str, str | None]:
    if "[" in token and token.endswith("]"):
        name, rep = token[:-1].split("[")
        return name, rep
    return token, None


def _select_rep(items: List[Any], rep: str | None) -> List[Any]:
    if rep == "*":
        return items
    if rep is None:
        return items[:1]
    idx = int(rep)
    return [items[idx]] if idx < len(items) else []


def _extract_values(msg: Dict[str, List[List[str]]], path: str) -> List[str]:
    parts = path.split(".")
    seg_name, seg_rep = _parse_token(parts[0])
    segs = _select_rep(msg.get(seg_name, []), seg_rep)
    results: List[str] = []
    for seg in segs:
        values: List[str] = [seg]
        level = 1
        for token in parts[1:]:
            name, rep = _parse_token(token)
            idx = int(name)
            next_vals: List[str] = []
            for val in values:
                if level == 1:  # field level
                    field = val[idx] if idx < len(val) else ""
                else:  # component level
                    comps = val.split("^") if isinstance(val, str) else val
                    field = comps[idx - 1] if idx - 1 < len(comps) else ""
                reps = field.split("~")
                if rep == "*":
                    next_vals.extend(reps)
                elif rep is None:
                    if reps:
                        next_vals.append(reps[0])
                else:
                    ri = int(rep)
                    if ri < len(reps):
                        next_vals.append(reps[ri])
            values = next_vals
            level += 1
        results.extend([v for v in values if v])
    return results


def _assign(obj: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        name, idx = _parse_index(p)
        if idx == "append":
            arr = cur.setdefault(name, [])
            new: Dict[str, Any] = {}
            arr.append(new)
            cur = new
        elif idx is None:
            cur = cur.setdefault(name, {})
        else:
            arr = cur.setdefault(name, [])
            while len(arr) <= idx:
                arr.append({})
            cur = arr[idx]
    leaf, idx = _parse_index(parts[-1])
    if idx == "append":
        arr = cur.setdefault(leaf, [])
        arr.append(value)
    elif idx is None:
        cur[leaf] = value
    else:
        arr = cur.setdefault(leaf, [])
        while len(arr) <= idx:
            arr.append(None)
        arr[idx] = value


def _parse_index(token: str) -> tuple[str, int | str | None]:
    if token.endswith("[]"):
        return token[:-2], "append"
    if "[" in token and token.endswith("]"):
        name, idx = token[:-1].split("[")
        return name, int(idx)
    return token, None


def _message_id(msg: Dict[str, List[List[str]]]) -> str:
    """Derive a deterministic message identifier from the MSH segment."""
    msh = msg.get("MSH", [])
    if msh:
        line = "|".join(msh[0])
        return str(uuid5(NAMESPACE_URL, line))
    return str(uuid4())


def _full_url(base: UUID, resource: str, index: int) -> str:
    """Deterministic urn:uuid for bundle entries."""
    return f"urn:uuid:{uuid5(base, f'{resource}/{index}')}"


def _run_qa(msg: Dict[str, List[List[str]]], rules_path: str | None) -> Dict[str, int]:
    """Placeholder QA hook."""
    # Real implementation would apply validation rules; keep stub for now
    return {"errors": 0, "warnings": 0}

def translate(
    input_path: str,
    rules: str | None = None,
    map_path: str | None = None,
    bundle: str | None = None,
    out: str = "out/",
    server: str | None = None,
    token: str | None = None,
    validate: bool = False,
    dry_run: bool = False,
) -> None:
    """Translate HL7 messages to FHIR resources."""

    base = Path(out)
    ndjson_dir = base / "fhir" / "ndjson"
    bundle_dir = base / "fhir" / "bundles"
    (base / "qa").mkdir(parents=True, exist_ok=True)
    ndjson_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (base / "deadletter").mkdir(parents=True, exist_ok=True)

    if not map_path:
        raise ValueError("map_path is required")
    spec: MapSpec = load_map(map_path)

    with open("config/fhir_target.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    defaults = cfg.get("default_profiles", {})

    text = Path(input_path).read_text(encoding="utf-8")
    msg = _parse_hl7(text)
    qa = _run_qa(msg, rules)

    resources: List[Dict[str, Any]] = []

    for plan in spec.resourcePlan:
        res: Dict[str, Any] = {"resourceType": plan.resource}
        profile = plan.profile or defaults.get(plan.resource)
        if profile:
            res.setdefault("meta", {})["profile"] = [profile]
        for rule in plan.rules:
            values = _extract_values(msg, rule.hl7_path)
            for v in values:
                if v == "" or v is None:
                    continue
                if rule.transform:
                    fn = getattr(transforms, rule.transform)
                    v = fn(v)
                _assign(res, rule.fhir_path, v)
        resources.append(res)

    msg_uuid = UUID(_message_id(msg))

    entries: List[tuple[Dict[str, Any], str]] = []
    for idx, r in enumerate(resources):
        fu = _full_url(msg_uuid, r["resourceType"], idx)
        r["id"] = fu.split(":")[-1]
        entries.append((r, fu))

    prov = {
        "resourceType": "Provenance",
        "recorded": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "agent": [{"type": {"text": "Silhouette HL7→FHIR"}}],
        "target": [{"reference": fu} for _, fu in entries],
        "entity": [
            {
                "role": "source",
                "what": {
                    "identifier": {
                        "system": "urn:silhouette:message",
                        "value": str(msg_uuid),
                    }
                },
            },
            {
                "role": "derivation",
                "what": {
                    "identifier": {
                        "system": "urn:silhouette:qa",
                        "value": json.dumps(qa),
                    }
                },
            },
        ],
    }
    prov_fu = _full_url(msg_uuid, "Provenance", len(entries))
    prov["id"] = prov_fu.split(":")[-1]
    entries.append((prov, prov_fu))

    # Write NDJSON
    by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r, _ in entries:
        by_type[r["resourceType"]].append(r)
    for rt, items in by_type.items():
        p = ndjson_dir / f"{rt}.ndjson"
        with p.open("w", encoding="utf-8") as fh:
            for item in items:
                fh.write(json.dumps(item) + "\n")

    if bundle == "transaction":
        bundle_res: Dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [],
        }
        for r, fu in entries:
            entry = {"fullUrl": fu, "resource": r, "request": {}}
            rt = r["resourceType"]
            if rt == "Patient":
                ident = r.get("identifier", [{}])[0]
                system = ident.get("system", "")
                value = ident.get("value", "")
                entry["request"] = {
                    "method": "PUT",
                    "url": f"Patient?identifier={system}|{value}",
                }
            elif rt == "Encounter":
                ident = r.get("identifier", [{}])[0]
                system = ident.get("system", "")
                value = ident.get("value", "")
                if system and value:
                    entry["request"] = {
                        "method": "PUT",
                        "url": f"Encounter?identifier={system}|{value}",
                    }
                else:
                    entry["request"] = {"method": "POST", "url": "Encounter"}
            else:
                entry["request"] = {"method": "POST", "url": rt}
            bundle_res["entry"].append(entry)
        out_path = bundle_dir / f"{Path(input_path).stem}.json"
        out_path.write_text(json.dumps(bundle_res, indent=2), encoding="utf-8")
