#!/usr/bin/env python
import argparse, json, pathlib, hashlib, random

def hash_prompt(p): return hashlib.sha256(p.encode()).hexdigest()

def load_traces(path):
    if not path.exists(): return []
    return [json.loads(l) for l in path.read_text().splitlines()]

def save_traces(path, items):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path,"w",encoding="utf-8") as f:
        for item in items: f.write(json.dumps(item)+"\n")

def curate(lane, sample=None):
    src = pathlib.Path("training_data/flywheel")/lane/"runtime.jsonl"
    dst = pathlib.Path("training_data/flywheel")/lane/"curated.jsonl"
    seen = set(); curated=[]
    for ex in load_traces(src):
        h = hash_prompt(ex.get("prompt",""))
        if h in seen: continue
        seen.add(h); curated.append(ex)
    if sample: curated = random.sample(curated, min(sample,len(curated)))
    save_traces(dst, curated)
    print(f"Curated {len(curated)} examples → {dst}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--lane",required=True)
    ap.add_argument("--sample",type=int,default=None)
    args=ap.parse_args()
    curate(args.lane,args.sample)
