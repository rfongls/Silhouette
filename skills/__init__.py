"""
Compat shim so legacy imports like `from skills.xyz import ...`
resolve to `silhouette_core.skills.xyz` after the refactor.
"""
import importlib, sys

_TARGET = "silhouette_core.skills"
pkg = importlib.import_module(_TARGET)
sys.modules[__name__] = pkg  # make `skills` alias the new package

# Best-effort subpackage aliasing (extend this list as you add skills)
for sub in [
    "cyber_common",
    "cyber_pentest_gate", "cyber_recon_scan",
    "cyber_netforensics", "cyber_ir_playbook", "cyber_extension",
]:
    try:
        sys.modules[f"{__name__}.{sub}"] = importlib.import_module(f"{_TARGET}.{sub}")
    except ModuleNotFoundError:
        pass

