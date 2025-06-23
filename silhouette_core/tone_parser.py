"""Basic tone parser placeholder."""


def score_tone(text: str) -> str:
    """Return a naive tone label."""
    lowered = text.lower()
    if any(x in lowered for x in ["!", "angry", "frustrated"]):
        return "negative"
    if any(x in lowered for x in [":)", "thank", "great"]):
        return "positive"
    return "neutral"

