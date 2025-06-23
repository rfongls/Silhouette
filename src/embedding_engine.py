from difflib import get_close_matches

def query_knowledge(memory_path, prompt, top_n=3):
    import json
    with open(memory_path, "r") as f:
        entries = [json.loads(line) for line in f]
    texts = [e["content"] for e in entries if "content" in e]
    matches = get_close_matches(prompt, texts, n=top_n, cutoff=0.4)
    return [entry for entry in entries if entry["content"] in matches]
