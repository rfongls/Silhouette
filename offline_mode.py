#!/usr/bin/env python3
"""
offline_mode.py

Detects offline state and provides safe-mode decorators/throttling.
"""

import os
import time
import functools
from pathlib import Path
from performance_profiler import get_cpu_load

def is_offline():
    """
    Returns True if persona.dsl or memory.jsonl are missing, or env var SILHOUETTE_OFFLINE is set.
    """
    if os.getenv('SILHOUETTE_OFFLINE') == '1':
        return True
    required = [Path('persona.dsl'), Path('memory.jsonl')]
    return any(not p.is_file() for p in required)

def throttle(min_interval: float):
    """
    Decorator to enforce minimum interval between function calls in offline mode.
    """
    def decorator(fn):
        last_called = {'time': 0.0}
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if is_offline():
                elapsed = time.time() - last_called['time']
                to_wait = min_interval - elapsed
                if to_wait > 0:
                    time.sleep(to_wait)
                last_called['time'] = time.time()
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def load_throttle(threshold: float, interval: float):
    """Delay execution when CPU load exceeds threshold."""

    def decorator(fn):
        base = throttle(interval)(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if get_cpu_load() > threshold:
                time.sleep(interval)
            return base(*args, **kwargs)

        return wrapper

    return decorator
