from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from hl7apy.parser import parse_message
from hl7apy.core import Message, Segment, Field, Component, SubComponent
import yaml

@dataclass
class MappingRule:
    hl7_path: str
    fhir_resource: str
    fhir_path: str
    transform: Optional[str] = None
    required: bool = False

class HL7v2ToFHIRTranslator:
    """Translate HL7 v2 text to FHIR Bundle using hl7apy and mapping rules."""

    def __init__(self, rules: List[MappingRule], profile_name: str = "USCore-R4", version: str = "2.5.1"):
        self.rules = rules
        self.profile_name = profile_name
        self.version = version

    def translate_text(self, hl7_text: str) -> Dict[str, Any]:
        msg = parse_message(hl7_text, validation_level=2)
        return self._translate_msg(msg)

    def _translate_msg(self, msg: Message) -> Dict[str, Any]:
        bundle: Dict[str, Any] = {"resourceType": "Bundle", "type": "collection", "entry": []}
        index: Dict[tuple, Dict[str, Any]] = {}

        def get_or_make(rt: str, key: Optional[str] = None) -> Dict[str, Any]:
            if key and (rt, key) in index:
                return index[(rt, key)]
            res: Dict[str, Any] = {"resourceType": rt}
            if key:
                index[(rt, key)] = res
            bundle["entry"].append({"resource": res})
            return res

        for rule in self.rules:
            values = self._extract_values(msg, rule.hl7_path)
            if (not values or all(v is None for v in values)) and rule.required:
                raise ValueError(f"Required HL7 path missing: {rule.hl7_path}")
            for v in values:
                if v is None:
                    continue
                if rule.transform:
                    v = self._apply_transform(v, rule.transform)
                target = get_or_make(rule.fhir_resource)
                self._assign(target, rule.fhir_path, v)
        return bundle

    def _extract_values(self, msg: Message, path: str) -> List[Any]:
        parts = path.split('.')
        current: List[Any] = [msg]
        for part in parts:
            name, rep = (part, None)
            if '[' in part and ']' in part:
                name, rep = part[:-1].split('[')
                rep = rep.strip()
            nxt: List[Any] = []
            for obj in current:
                if isinstance(obj, Message):
                    segs = getattr(obj, name, [])
                    if not isinstance(segs, list):
                        segs = [segs]
                    if rep == '*':
                        nxt.extend(segs)
                    elif rep is None:
                        nxt.extend(segs[:1])
                    else:
                        idx = int(rep)
                        if idx < len(segs):
                            nxt.append(segs[idx])
                elif isinstance(obj, Segment) or isinstance(obj, Field):
                    if isinstance(obj, Segment):
                        fld_idx = int(name)
                        fields = [f for f in obj.children if isinstance(f, Field) and f.position == fld_idx]
                        if rep == '*':
                            nxt.extend(fields)
                        elif rep is None:
                            if fields:
                                nxt.append(fields[0])
                        else:
                            idx = int(rep)
                            if idx < len(fields):
                                nxt.append(fields[idx])
                    else:  # Field
                        comp_idx = int(name)
                        comps = [c for c in obj.children if isinstance(c, Component) and c.position == comp_idx]
                        if rep == '*':
                            nxt.extend(comps)
                        elif rep is None:
                            if comps:
                                nxt.append(comps[0])
                        else:
                            idx = int(rep)
                            if idx < len(comps):
                                nxt.append(comps[idx])
                elif isinstance(obj, Component):
                    sub_idx = int(name)
                    subs = [s for s in obj.children if isinstance(s, SubComponent) and s.position == sub_idx]
                    if rep == '*':
                        nxt.extend(subs)
                    elif rep is None:
                        if subs:
                            nxt.append(subs[0])
                    else:
                        idx = int(rep)
                        if idx < len(subs):
                            nxt.append(subs[idx])
            current = nxt
        values: List[Any] = []
        for o in current:
            try:
                if hasattr(o, 'value'):
                    values.append(o.value)
                else:
                    values.append(str(o))
            except Exception:
                values.append(None)
        return values or [None]

    def _assign(self, obj: Dict[str, Any], path: str, value: Any) -> None:
        keys = path.split('.')
        cur = obj
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        leaf = keys[-1]
        if leaf.endswith('[]'):
            leaf = leaf[:-2]
            cur.setdefault(leaf, [])
            cur[leaf].append(value)
        else:
            cur[leaf] = value

    def _apply_transform(self, value: Any, transform: str) -> Any:
        if transform == 'toDate':
            return str(value)[:10]
        if transform == 'decimal':
            try:
                return float(value)
            except Exception:
                return value
        if transform.startswith('loinc:'):
            code = str(value).strip()
            return {'system': 'http://loinc.org', 'code': code}
        return value

def load_rules(path: str) -> List[MappingRule]:
    raw = yaml.safe_load(open(path))
    return [MappingRule(**r) for r in raw['resources']]
