"""
Compat shim to redirect legacy `skills` imports to `silhouette_core.skills`.
"""
import importlib, sys
_TARGET = "silhouette_core.skills"
pkg = importlib.import_module(_TARGET)
sys.modules[__name__] = pkg
def __getattr__(name):
    mod = importlib.import_module(f"{_TARGET}.{name}")
    sys.modules[f"{__name__}.{name}"] = mod
    return mod
