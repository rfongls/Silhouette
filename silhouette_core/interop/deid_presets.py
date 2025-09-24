from __future__ import annotations
import random
from datetime import datetime, timedelta

# --- Primitives reused by presets ---
def _random_name_pair(rng: random.Random) -> tuple[str, str]:
    first_names = ["Donald","Mickey","Chris","Laura","Mike","Linda","Robert","Mary","David","Sarah","James","Karen","Brian","Nancy","Jason"]
    last_names  = ["Mouse","Duck","Frankenstein","Smith","Doe","Brown","Johnson"]
    return rng.choice(first_names), rng.choice(last_names)

def _random_date(rng: random.Random) -> str:
    start_date = datetime(1970, 1, 1)
    end_date   = datetime(1995, 12, 31)
    dt = start_date + timedelta(days=rng.randrange((end_date - start_date).days))
    return dt.strftime("%Y%m%d")

def _random_datetime(rng: random.Random) -> str:
    start_date = datetime(2000, 1, 1)
    end_date   = datetime(2025, 12, 31)
    dt = start_date + timedelta(seconds=rng.randint(0, int((end_date - start_date).total_seconds())))
    return dt.strftime("%Y%m%d%H%M%S")

def _random_gender(rng: random.Random) -> str:
    return rng.choice(["M","F"])

def _random_phone(rng: random.Random) -> str:
    return f"({rng.randint(100,999)}){rng.randint(100,999)}-{rng.randint(1000,9999)}"

def _random_address(rng: random.Random) -> str:
    # HL7 XAD: street^city^state^zip^country
    samples = [
        ["124 Conch St", "Bikini Bottom", "PO", "62704", "USA"],
        ["1640 Riverside Drive", "Hill Valley", "CA", "90210", "USA"],
        ["1313 Webfoot Wal", "Duckburg", "CA", "10001", "USA"],
    ]
    street, city, state, zipc, country = rng.choice(samples)
    return "^".join([street, city, state, zipc, country])

def _random_language(rng: random.Random) -> str:
    return rng.choice(["English","Chinese","German","Russian","French"])

def _random_race(rng: random.Random) -> str:
    return rng.choice(["Caucasian","Asian","African American","Hispanic or Latino","Native American"])

def _random_mrn(rng: random.Random) -> str:
    return f"{rng.randint(100000, 999999)}"

def _random_ssn(rng: random.Random) -> str:
    return f"{rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"

def _random_facility(rng: random.Random) -> str:
    ids = ["99999","88888","77777"]
    names = ["Healthcare Center","Wellness Hospital","Psychiatric Clinic"]
    addrs = ["111 Gotham City, New York, USA","222 Asgard, Valhalla, USA","333 The Emerald City, Oz, USA"]
    return f"{rng.choice(ids)}^{rng.choice(names)}^{rng.choice(addrs)}"

# --- Public preset API ---
def gen_preset(preset_key: str, *, seed: int | None = None) -> str:
    """
    Generate a synthetic value for a named preset. Stable within one call if seed supplied.
    """
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    key = (preset_key or "").strip().lower()

    if key in ("name", "person_name", "xpn"):
        # HL7 XPN is typically Family^Given; some of your prior code used Given^Family.
        first, last = _random_name_pair(rng)
        return f"{last}^{first}"

    if key in ("birthdate", "dob", "date"):
        return _random_date(rng)

    if key in ("datetime", "date/time", "timestamp"):
        return _random_datetime(rng)

    if key in ("gender", "sex"):
        return _random_gender(rng)

    if key in ("address", "xad"):
        return _random_address(rng)

    if key in ("phone", "xtn"):
        return _random_phone(rng)

    if key in ("language", "lang"):
        return _random_language(rng)

    if key in ("race",):
        return _random_race(rng)

    if key in ("mrn",):
        return _random_mrn(rng)

    if key in ("ssn", "social", "nin"):
        return _random_ssn(rng)

    if key in ("facility",):
        return _random_facility(rng)

    if key in ("note", "nte"):
        return f"Note {rng.randint(1,100)}: [De-identified data]"

    if key in ("pdf_blob", "pdf", "jvber"):
        return "JVBERi0xLjQNCiX5abcdefghi0k"

    if key in ("xml_blob", "xml", "pd94"):
        return "PD940xLjQNCiX5abcdefghi0k"

    # Fallback empty literal (acts like redact)
    return ""
