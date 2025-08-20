from typing import Dict, Any, List
from dataclasses import dataclass
import json

@dataclass
class MappingRule:
    hl7_path: str
    fhir_resource: str
    fhir_path: str
    transform: str | None = None
    required: bool = False

class HL7v2ToFHIRTranslator:
    """
    Applies YAML mapping rules (profiles/hl7v2_*.yml) to HL7 v2 parsed structures.
    The HL7 parser is assumed to yield a dict-of-dicts with segments, fields, components.
    """

    def __init__(self, mapping_rules: List[MappingRule], profile_name: str = "USCore-R4"):
        self.rules = mapping_rules
        self.profile_name = profile_name

    def translate(self, hl7_dict: Dict[str, Any]) -> Dict[str, Any]:
        bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
        index: Dict[str, Dict[str, Any]] = {}

        def get_or_make(rt: str, key: str | None = None) -> Dict[str, Any]:
            if key and (rt, key) in index:
                return index[(rt, key)]
            res = {"resourceType": rt}
            if key:
                index[(rt, key)] = res
            bundle["entry"].append({"resource": res})
            return res

        for rule in self.rules:
            value = self._extract(hl7_dict, rule.hl7_path)
            if value is None and rule.required:
                raise ValueError(f"Required HL7 path missing: {rule.hl7_path}")

            if value is None:
                continue

            if rule.transform:
                value = self._apply_transform(value, rule.transform)

            target = get_or_make(rule.fhir_resource)
            self._assign(target, rule.fhir_path, value)

        return bundle

    def _extract(self, hl7: Dict[str, Any], path: str):
        parts = path.split('.')
        cur = hl7
        for p in parts:
            if '[' in p and ']' in p:
                name, idx = p[:-1].split('[')
                if idx == '*':
                    seq = cur.get(name, [])
                    return [self._extract(x, '.'.join(parts[parts.index(p)+1:])) for x in seq]
                else:
                    i = int(idx)
                    cur = cur.get(name, [])[i]
            else:
                cur = cur.get(p)
            if cur is None:
                return None
        return cur

    def _assign(self, obj: Dict[str, Any], path: str, value: Any):
        keys = path.split('.')
        cur = obj
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        leaf = keys[-1]
        if leaf.endswith('[]'):
            leaf = leaf[:-2]
            cur.setdefault(leaf, [])
            if isinstance(value, list):
                cur[leaf].extend(value)
            else:
                cur[leaf].append(value)
        else:
            cur[leaf] = value

    def _apply_transform(self, value: Any, transform: str):
        if transform == "toDate":
            return str(value)[:10]
        if transform.startswith("loinc:"):
            code = value
            return {"coding": [{"system": "http://loinc.org", "code": code}]}
        if transform == "decimal":
            try:
                return float(value)
            except Exception:
                return value
        if transform.startswith("concat("):
            parts = transform[len("concat("):-1].split(',')
            out = []
            for p in parts:
                p = p.strip().strip('\'"')
                if p == "{value}":
                    out.append(str(value))
                else:
                    out.append(p)
            return ''.join(out)
        return value
