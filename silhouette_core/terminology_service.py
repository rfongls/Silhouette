import json
import os
from pathlib import Path
from typing import Optional
import requests

_CACHE_DIR = Path(os.getenv("TERMINOLOGY_CACHE_DIR", Path(__file__).resolve().parents[1] / "terminology" / "valuesets"))


def _safe_name(url: str) -> str:
    return url.replace("://", "_").replace("/", "_").replace(".", "_") + ".json"


def _load_valueset(url: str, cache_dir: Path) -> dict:
    path = cache_dir / _safe_name(url)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def validate_code(system: str, code: str, vs_url: str, cache_dir: Optional[str] = None, tx_url: Optional[str] = None) -> bool:
    cache = Path(cache_dir) if cache_dir else _CACHE_DIR
    vs = _load_valueset(vs_url, cache)
    for inc in vs.get("compose", {}).get("include", []):
        if system and inc.get("system") != system:
            continue
        for concept in inc.get("concept", []):
            if concept.get("code") == code:
                return True
    if tx_url:
        try:
            resp = requests.get(
                f"{tx_url}/ValueSet/$validate-code",
                params={"url": vs_url, "code": code, "system": system},
                timeout=5,
            )
            if resp.ok and resp.json().get("result"):
                return True
        except Exception:
            pass
    return False


def validate_resource(resource: dict, cache_dir: Optional[str] = None, tx_url: Optional[str] = None) -> bool:
    """Validate known codings within a resource.

    Currently only checks Observation.code against LOINC ValueSet.
    """
    rtype = resource.get("resourceType")
    if rtype == "Observation":
        for coding in resource.get("code", {}).get("coding", []):
            if not validate_code(coding.get("system"), coding.get("code"), "http://loinc.org", cache_dir, tx_url):
                return False
    return True
