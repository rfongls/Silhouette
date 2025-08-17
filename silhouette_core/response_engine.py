import os


def generate_text(prompt: str) -> str:
    """Return model output or a deterministic offline stub.

    Preference order:
    1. `STUDENT_MODEL` environment variable
    2. `SILHOUETTE_DEFAULT_MODEL` environment variable
    3. tiny open-weight model
    """
    model_name = (
        os.environ.get("STUDENT_MODEL")
        or os.environ.get("SILHOUETTE_DEFAULT_MODEL")
        or "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    )

    try:
        from transformers import pipeline  # type: ignore

        nlp = pipeline("text-generation", model=model_name, trust_remote_code=True)
        outs = nlp(prompt, max_new_tokens=256, temperature=0.7, top_p=0.9)
        text = outs[0]["generated_text"]
        return text[len(prompt):].strip() if text.startswith(prompt) else text.strip()
    except Exception:
        lower = prompt.lower()
        if "agent" in lower:
            return "An agent decides and acts using tools to reach goals."

        return f"[offline-stub] Agent received: {prompt[:120]} ..."
