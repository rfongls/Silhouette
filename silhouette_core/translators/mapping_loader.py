"""Load YAML mapping profiles for HL7→FHIR translation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class Rule:
    hl7_path: str
    fhir_path: str
    transform: Optional[str] = None


@dataclass
class ResourcePlan:
    resource: str
    profile: Optional[str] = None
    rules: List[Rule] = field(default_factory=list)


@dataclass
class MapSpec:
    messageTypes: List[str]
    resourcePlan: List[ResourcePlan]


def load(path: str) -> MapSpec:
    """Load a mapping specification from YAML."""
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    plans: List[ResourcePlan] = []
    for rp in raw.get("resourcePlan", []):
        rules = [Rule(**r) for r in rp.get("rules", [])]
        plans.append(ResourcePlan(resource=rp["resource"], profile=rp.get("profile"), rules=rules))
    return MapSpec(messageTypes=raw.get("messageTypes", []), resourcePlan=plans)
