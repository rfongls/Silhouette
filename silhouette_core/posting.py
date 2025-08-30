import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


def post_transaction(
    bundle: Dict[str, Any],
    server: str,
    token: str | None,
    timeout: int = 20,
    max_retries: int = 3,
    deadletter_dir: str = "out/deadletter",
) -> tuple[bool, int, int]:
    """Post a FHIR transaction Bundle with retry and dead-letter support.

    Returns a tuple of (posted, status_code, latency_ms).
    """
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
        "Prefer": "handling=strict",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = server.rstrip("/")
    attempt = 0
    start = time.time()
    response: requests.Response | None = None
    while attempt <= max_retries:
        attempt += 1
        try:
            response = requests.post(url, json=bundle, headers=headers, timeout=timeout)
            status = response.status_code
            if status == 429 or 500 <= status < 600:
                if attempt <= max_retries:
                    delay = (2 ** (attempt - 1)) + random.random()
                    logger.warning(
                        "post attempt %s failed with %s; retrying in %.2fs", attempt, status, delay
                    )
                    time.sleep(delay)
                    continue
            break
        except requests.RequestException as exc:  # network issues
            status = getattr(exc.response, "status_code", 0)
            if attempt <= max_retries:
                delay = (2 ** (attempt - 1)) + random.random()
                logger.warning(
                    "post attempt %s raised %s; retrying in %.2fs", attempt, exc, delay
                )
                time.sleep(delay)
                continue
            break
    latency_ms = int((time.time() - start) * 1000)
    posted = response is not None and 200 <= response.status_code < 300
    status = response.status_code if response is not None else 0
    if not posted:
        msg_id = bundle.get("id", "unknown")
        dl = Path(deadletter_dir)
        dl.mkdir(parents=True, exist_ok=True)
        (dl / f"{msg_id}_request.json").write_text(
            json.dumps(bundle, indent=2), encoding="utf-8"
        )
        body = response.text if response is not None else ""
        (dl / f"{msg_id}_response.json").write_text(body, encoding="utf-8")
    return posted, status, latency_ms
