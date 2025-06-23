import os
import json
from datetime import datetime

def load_knowledge_from_markdown(path):
    entries = []
    with open(path, 'r') as f:
        section = None
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                section = line.lstrip('#').strip()
            elif line:
                entries.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "section": section,
                    "content": line
                })
    return entries

def save_to_memory(entries, memory_path="logs/memory.jsonl"):
    with open(memory_path, "a") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

def train_from_knowledge_store(store_dir="knowledge_store"):
    for file in os.listdir(store_dir):
        if file.endswith(".md"):
            full_path = os.path.join(store_dir, file)
            entries = load_knowledge_from_markdown(full_path)
            save_to_memory(entries)
            print(f"Ingested {len(entries)} entries from {file}")

if __name__ == "__main__":
    train_from_knowledge_store()
