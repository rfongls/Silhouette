import json
import os
from datetime import datetime

MEMORY_FILE = "logs/memory.jsonl"

def append_to_memory(entry):
    entry["timestamp"] = datetime.utcnow().isoformat()
    with open(MEMORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def query_memory(keyword):
    if not os.path.exists(MEMORY_FILE):
        return []
    results = []
    with open(MEMORY_FILE, "r") as f:
        for line in f:
            entry = json.loads(line)
            if keyword.lower() in json.dumps(entry).lower():
                results.append(entry)
    return results
