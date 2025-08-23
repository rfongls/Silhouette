import os


def is_offline() -> bool:
    """Return True if the SILHOUETTE_OFFLINE environment variable is truthy."""
    return os.getenv("SILHOUETTE_OFFLINE") not in (None, "", "0")

