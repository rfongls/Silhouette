import json
import os
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def load_memory_texts(memory_path):
    with open(memory_path, 'r') as f:
        entries = [json.loads(line) for line in f]
    texts = [entry.get("content", "") for entry in entries]
    return entries, texts

def query_similarity(prompt, texts, top_n=3):
    vectorizer = TfidfVectorizer().fit(texts + [prompt])
    vectors = vectorizer.transform(texts + [prompt])
    similarities = cosine_similarity(vectors[-1], vectors[:-1]).flatten()
    top_indices = similarities.argsort()[-top_n:][::-1]
    return top_indices, similarities

def query_knowledge(memory_path="logs/memory.jsonl", prompt="", top_n=3):
    if not os.path.exists(memory_path):
        print(f"[!] Memory file not found: {memory_path}")
        return []

    entries, texts = load_memory_texts(memory_path)
    top_indices, sims = query_similarity(prompt, texts, top_n)

    results = []
    for idx in top_indices:
        entry = entries[idx]
        entry["score"] = round(float(sims[idx]), 3)
        results.append(entry)
    return results

if __name__ == "__main__":
    # Simple test
    result = query_knowledge(prompt="What is the HL7 delimiter?")
    for r in result:
        print(f"[{r['score']}] {r['content']}")
