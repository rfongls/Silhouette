def detect_tone(text):
    tone_keywords = {
        "angry": ["hate", "mad", "angry", "furious"],
        "happy": ["love", "great", "happy", "excited"],
        "confused": ["what", "confused", "unsure", "unclear"],
        "neutral": []
    }

    scores = {tone: 0 for tone in tone_keywords}
    for tone, keywords in tone_keywords.items():
        scores[tone] = sum(text.lower().count(k) for k in keywords)

    best_tone = max(scores, key=scores.get)
    return {
        "tone": best_tone,
        "confidence": 0.9 if scores[best_tone] > 0 else 0.5
    }
