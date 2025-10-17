from __future__ import annotations
from typing import Dict, Any, Tuple

# Import ONLY stable, non-V2-specific functions. If these move in your tree,
# you can update these imports without touching V2 modules/routes/templates.
from api.interop_gen import generate_messages, _normalize_validation_result
from silhouette_core.interop.deid import apply_deid_with_template
from silhouette_core.interop.validate_workbook import validate_with_template

def do_generate(form: Dict[str, Any]) -> str:
    """
    form keys expected (legacy-compatible): 'message', 'trigger' (optional)
    """
    return generate_messages(form)

def do_deidentify(message: str, template: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (deidentified_text, summary_dict)
    """
    text = apply_deid_with_template(message, template)
    return text, {"template_used": template.get("name", "default")}

def do_validate(message: str, template: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns normalized validation result dict; caller decides render.
    """
    raw = validate_with_template(message, template)
    return _normalize_validation_result(raw)
