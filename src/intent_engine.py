import json
from difflib import get_close_matches

class IntentEngine:
    def __init__(self, examples_file="INTENT_EXAMPLES.json"):
        with open(examples_file, "r") as f:
            self.examples = json.load(f)["examples"]
        self.intents = {e["phrase"]: e["intent"] for e in self.examples}

    def classify(self, phrase):
        close = get_close_matches(phrase, self.intents.keys(), n=1, cutoff=0.5)
        if close:
            return {"intent": self.intents[close[0]], "confidence": 0.9}
        return {"intent": "unknown", "confidence": 0.2}
