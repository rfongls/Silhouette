
from datetime import datetime

def format_response(user_input, mode="structured"):
    timestamp = datetime.utcnow().isoformat()
    if mode == "structured":
        return f"[Structured @ {timestamp}] Silhouette: I have received your message: '{user_input}'. Let's explore it."
    elif mode == "empathic":
        return f"Silhouette (Empathic): I understand this may be complex. Let's work through it together. You said: '{user_input}'"
    elif mode == "raw":
        return f"You said: {user_input}"
    else:
        return f"[Fallback] Silhouette: I’m not sure how to format this, but I hear you: '{user_input}'"

def get_response(user_input, alignment):
    mode = alignment.get("values", {}).get("response_mode", "structured")
    return format_response(user_input, mode)
