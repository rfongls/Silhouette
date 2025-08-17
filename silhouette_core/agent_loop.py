from silhouette_core.alignment_engine import load_persona_config, violates_alignment, format_response
from silhouette_core.response_engine import generate_text
from silhouette_core.tools import ToolRegistry

PERSONA_PATH = "docs/alignment_kernel/persona.dsl"

class Agent:
    """
    Minimal agent loop:
      - Alignment gate (deny_on)
      - Tool call when user types `use:<tool> ...`
      - Otherwise call model generator (or offline stub)
    """
    def __init__(self, persona_path: str = PERSONA_PATH):
        self.persona = load_persona_config(persona_path)
        self.tools = ToolRegistry()

    def loop(self, user_msg: str) -> str:
        deny_list = self.persona.get("limits", {}).get("deny_on", [])
        if violates_alignment(user_msg, deny_list):
            return format_response(
                "I'm not permitted to assist with that request.",
                self.persona["tone"].get("style")
            )

        # Explicit tool-use protocol: "use:<tool> <args>"
        if user_msg.lower().startswith("use:"):
            parts = user_msg.split(None, 1)
            head = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            tool_name = head.split(":", 1)[1].strip()
            result = self.tools.invoke(tool_name, rest.strip())
            return format_response(str(result), self.persona["tone"].get("style"))

        # Default path: generate model text (or offline stub)
        text = generate_text(user_msg)
        return format_response(text, self.persona["tone"].get("style"))
