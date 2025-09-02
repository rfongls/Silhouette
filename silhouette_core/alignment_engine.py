def load_persona_config(path="docs/alignment_kernel/persona.dsl"):
    config = {"tone": {}, "limits": {"deny_on": []}}
    current = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = line[1:-1]
            elif "=" in line and current:
                key, val = (s.strip() for s in line.split("=", 1))
                if current == "limits" and key == "deny_on":
                    config[current][key] = [v.strip() for v in val.split(",")]
                else:
                    config[current][key] = val
    return config

def violates_alignment(prompt, deny_list):
    return any(term in prompt.lower() for term in deny_list)

def format_response(text, tone_style):
    if tone_style == "friendly":
        return f"😊 {text}"
    elif tone_style == "formal":
        return f"Silhouette: {text}"
    return text
