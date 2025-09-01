import json
from functools import lru_cache
from pathlib import Path

CVE_SEED = Path('data/security/seeds/cve/cve_seed.json')
KEV_SEED = Path('data/security/seeds/kev/kev_seed.json')


@lru_cache()
def _load_cve():
    return json.loads(CVE_SEED.read_text()) if CVE_SEED.exists() else {}


@lru_cache()
def _load_kev():
    return json.loads(KEV_SEED.read_text()).get('cves', []) if KEV_SEED.exists() else []


def get_cve(cve_id: str):
    return _load_cve().get(cve_id)


def is_kev(cve_id: str) -> bool:
    return cve_id in _load_kev()
