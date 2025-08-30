"""Minimal HL7 v2 → FHIR translation pipeline."""
from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import requests
import yaml

from translators import transforms
from translators.mapping_loader import load as load_map, MapSpec
from silhouette_core.posting import post_transaction
from skills import audit

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _remote_validate(server: str, token: str | None, resource: Dict[str, Any]) -> None:
    """POST resource to FHIR server's $validate endpoint."""
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
        "Prefer": "handling=strict",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = server.rstrip("/") + "/$validate"
    resp = requests.post(url, json=resource, headers=headers)
    resp.raise_for_status()


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
    message_mode: bool = False,
    partner: str | None = None,
    message_endpoint: str | None = None,
    notify_url: str | None = None,
    deidentify: bool = False,
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
    with open("config/identifier_systems.yaml", "r", encoding="utf-8") as f:
        id_systems = yaml.safe_load(f)
    defaults = cfg.get("default_profiles", {})
    if partner:
        partner_path = Path("config/partners") / f"{partner}.yaml"
        if partner_path.exists():
            p_cfg = yaml.safe_load(partner_path.read_text(encoding="utf-8")) or {}
            defaults.update(p_cfg.get("profiles", {}))

    text = Path(input_path).read_text(encoding="utf-8")
    msg = _parse_hl7(text)
    msg_type = msg.get("MSH", [])[0][8] if msg.get("MSH") and len(msg["MSH"][0]) > 8 else ""
    qa = _run_qa(msg, rules)
    metrics: Dict[str, int] = {}

    resources: List[Dict[str, Any]] = []

    for plan in spec.resourcePlan:
        res: Dict[str, Any] = {"resourceType": plan.resource}
        profile = defaults.get(plan.resource) or plan.profile
        if profile:
            res.setdefault("meta", {})["profile"] = [profile]
        for rule in plan.rules:
            if "|" in rule.hl7_path:
                paths = rule.hl7_path.split("|")
                vals = []
                for p in paths:
                    ext = _extract_values(msg, p)
                    vals.append(ext[0] if ext else None)
                if rule.transform:
                    fn = getattr(transforms, rule.transform)
                    try:
                        v = fn(*vals, metrics=metrics)
                    except TypeError:
                        v = fn(*vals)
                else:
                    v = vals[0]
                if v not in ("", None, {}):
                    if rule.fhir_path.endswith("[x]") and isinstance(v, dict):
                        for k, val in v.items():
                            if val not in ("", None, {}):
                                _assign(res, k, val)
                    else:
                        _assign(res, rule.fhir_path, v)
                continue
            if rule.hl7_path == "-":
                values = [None]
            else:
                values = _extract_values(msg, rule.hl7_path)
            for v in values:
                if v == "" or v is None:
                    if rule.hl7_path != "-":
                        continue
                if rule.transform:
                    fn = getattr(transforms, rule.transform)
                    if rule.hl7_path == "-":
                        try:
                            v = fn(metrics=metrics)
                        except TypeError:
                            v = fn()
                    else:
                        try:
                            v = fn(v, metrics=metrics)
                        except TypeError:
                            v = fn(v)
                if v == "" or v is None or v == {}:
                    continue
                if rule.fhir_path.endswith("[x]") and isinstance(v, dict):
                    for k, val in v.items():
                        if val not in ("", None, {}):
                            _assign(res, k, val)
                else:
                    _assign(res, rule.fhir_path, v)
        resources.append(res)

    if deidentify:
        for r in resources:
            if r.get("resourceType") == "Patient":
                r.pop("name", None)

    if validate:
        from validators.fhir_profile import (
            validate_structural_with_pydantic,
            validate_uscore_jsonschema,
        )
        for res in resources:
            validate_uscore_jsonschema(res)
            validate_structural_with_pydantic(res)
            if server:
                _remote_validate(server, token, res)

    msg_uuid = UUID(_message_id(msg))

    entries: List[tuple[Dict[str, Any], str]] = []
    for idx, r in enumerate(resources):
        fu = _full_url(msg_uuid, r["resourceType"], idx)
        r["id"] = fu.split(":")[-1]
        entries.append((r, fu))

    obs_refs = [
        {"reference": fu} for r, fu in entries if r["resourceType"] == "Observation"
    ]
    for r, _ in entries:
        if r["resourceType"] == "DiagnosticReport" and obs_refs:
            r.setdefault("result", []).extend(obs_refs)

    # Resolve identifier-based references
    lookup: Dict[tuple[str, str], str] = {}
    for res, fu in entries:
        ids = res.get("identifier")
        if isinstance(ids, list):
            for ident in ids:
                sys = ident.get("system")
                val = ident.get("value")
                if sys and val:
                    lookup[(sys, val)] = fu
    for res, _ in entries:
        if res["resourceType"] == "Appointment":
            for part in res.get("participant", []):
                actor = part.get("actor", {})
                ident = actor.get("identifier")
                if ident:
                    fu = lookup.get((ident.get("system"), ident.get("value")))
                    if fu:
                        actor["reference"] = fu
        elif res["resourceType"] == "PractitionerRole":
            for key in ("practitioner", "organization", "location"):
                ref = res.get(key)
                if isinstance(ref, dict):
                    ident = ref.get("identifier")
                    if ident:
                        fu = lookup.get((ident.get("system"), ident.get("value")))
                        if fu:
                            ref["reference"] = fu
        else:
            for key in ("organization", "location", "practitioner"):
                ref = res.get(key)
                if isinstance(ref, dict):
                    ident = ref.get("identifier")
                    if ident:
                        fu = lookup.get((ident.get("system"), ident.get("value")))
                        if fu:
                            ref["reference"] = fu

    if validate:
        from validators.fhir_profile import (
            validate_structural_with_pydantic,
            validate_uscore_jsonschema,
        )
        for r, _ in entries:
            validate_uscore_jsonschema(r)
            validate_structural_with_pydantic(r)
            if server:
                _remote_validate(server, token, r)

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
    prov.setdefault("meta", {})["profile"] = [defaults.get("Provenance", "http://hl7.org/fhir/StructureDefinition/Provenance")]
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

    bundle_res: Dict[str, Any] | None = None
    if message_mode:
        header = {
            "resourceType": "MessageHeader",
            "eventCoding": {"code": msg_type},
            "source": {"name": "Silhouette HL7→FHIR"},
            "focus": [{"reference": fu} for _, fu in entries],
        }
        header_fu = _full_url(msg_uuid, "MessageHeader", len(entries))
        header["id"] = header_fu.split(":")[-1]
        bundle_res = {
            "resourceType": "Bundle",
            "type": "message",
            "id": str(msg_uuid),
            "entry": [{"fullUrl": header_fu, "resource": header}],
        }
        for r, fu in entries:
            bundle_res["entry"].append({"fullUrl": fu, "resource": r})
    elif bundle == "transaction":
        bundle_res = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [],
            "id": str(msg_uuid),
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
            elif rt == "ServiceRequest":
                ident = r.get("identifier", [{}])[0]
                system = ident.get("system", "")
                value = ident.get("value", "")
                if system and value:
                    entry["request"] = {
                        "method": "PUT",
                        "url": f"ServiceRequest?identifier={system}|{value}",
                    }
                else:
                    entry["request"] = {"method": "POST", "url": "ServiceRequest"}
            elif rt == "Appointment":
                ident = r.get("identifier", [{}])[0]
                system = ident.get("system", "")
                value = ident.get("value", "")
                if system and value:
                    entry["request"] = {
                        "method": "PUT",
                        "url": f"Appointment?identifier={system}|{value}",
                    }
                else:
                    entry["request"] = {"method": "POST", "url": "Appointment"}
            elif rt in ("Organization", "Practitioner", "PractitionerRole", "Location"):
                ident = r.get("identifier", [{}])[0]
                system = ident.get("system", "") or id_systems.get(rt.lower(), "")
                value = ident.get("value", "")
                if system and value:
                    entry["request"] = {
                        "method": "PUT",
                        "url": f"{rt}?identifier={system}|{value}",
                    }
                else:
                    entry["request"] = {"method": "POST", "url": rt}
            else:
                entry["request"] = {"method": "POST", "url": rt}
            bundle_res["entry"].append(entry)

    if bundle_res:
        out_path = bundle_dir / f"{Path(input_path).stem}.json"
        out_path.write_text(json.dumps(bundle_res, indent=2), encoding="utf-8")

        resource_counts = {k: len(v) for k, v in by_type.items()}
        fhir_count = len(entries) + (1 if message_mode else 0)
        tx_miss = metrics.get("tx-miss", 0)
        qa_status = "ok" if qa.get("errors", 0) == 0 else "fail"
        posted = False
        status = 0
        latency_ms = 0
        dead_letter = False

        if message_mode and message_endpoint and not dry_run:
            try:
                resp = requests.post(message_endpoint, json=bundle_res)
                status = resp.status_code
                posted = resp.ok
            except requests.RequestException:
                dead_letter = True
                status = 0
        elif server and not dry_run and not message_mode:
            if validate:
                try:
                    _remote_validate(server, token, bundle_res)
                except requests.HTTPError as exc:
                    dead_letter = True
                    resp = exc.response
                    dl = base / "deadletter"
                    (dl / f"{msg_uuid}_request.json").write_text(
                        json.dumps(bundle_res, indent=2), encoding="utf-8"
                    )
                    body = resp.text if resp is not None else str(exc)
                    (dl / f"{msg_uuid}_response.json").write_text(body, encoding="utf-8")
                    status = resp.status_code if resp is not None else 0
                else:
                    posted, status, latency_ms = post_transaction(
                        bundle_res, server, token, deadletter_dir=str(base / "deadletter")
                    )
                    dead_letter = not posted
            else:
                posted, status, latency_ms = post_transaction(
                    bundle_res, server, token, deadletter_dir=str(base / "deadletter")
                )
                dead_letter = not posted

        metrics_path = base / "metrics.csv"
        if not metrics_path.exists():
            with metrics_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "messageId",
                        "type",
                        "qaStatus",
                        "fhirCount",
                        "posted",
                        "latencyMs",
                        "txMisses",
                        "postedCount",
                        "deadLetter",
                    ]
                )
        with metrics_path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    str(msg_uuid),
                    msg_type,
                    qa_status,
                    fhir_count,
                    posted,
                    latency_ms,
                    tx_miss,
                    fhir_count if posted else 0,
                    dead_letter,
                ]
            )

        log_entry = {
            "ts": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "messageId": str(msg_uuid),
            "phase": "post",
            "posted": posted,
            "status": status,
            "txMisses": tx_miss,
            "resourceCounts": resource_counts,
        }
        logger.info(json.dumps(log_entry))

        if notify_url:
            payload = {"messageId": str(msg_uuid), "resourceCounts": resource_counts}
            for _ in range(3):
                try:
                    requests.post(notify_url, json=payload, timeout=5)
                    break
                except Exception:
                    continue

        audit.emit_and_persist(
            audit.fhir_audit_event("translate", "success", "cli", str(msg_uuid))
        )