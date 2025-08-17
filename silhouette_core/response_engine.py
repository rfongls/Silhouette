def generate_text(prompt: str) -> str:
    """
    Minimal model call:
      - Try local HF transformers pipeline (no billing)
      - Else return deterministic offline stub
    """
    try:
        from transformers import pipeline  # type: ignore
        nlp = pipeline(
            "text-generation",
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            trust_remote_code=True
        )
        outs = nlp(prompt, max_new_tokens=256, temperature=0.7, top_p=0.9)
        text = outs[0]["generated_text"]
        return text[len(prompt):].strip() if text.startswith(prompt) else text.strip()
    except Exception:
        return f"[offline-stub] {prompt[:120]} ..."
