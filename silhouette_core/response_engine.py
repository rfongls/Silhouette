from silhouette_core.alignment_engine import (
    load_persona_config,
    violates_alignment,
    format_response,
)

persona = load_persona_config()

def get_response(prompt, alignment):
    if violates_alignment(prompt, persona["limits"]["deny_on"]):
        return format_response("I'm not permitted to assist with that request.", persona["tone"].get("style"))
    return format_response("Acknowledged. Processing your request...", persona["tone"].get("style"))
