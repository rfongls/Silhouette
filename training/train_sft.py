import argparse
import yaml
from transformers import AutoTokenizer
import torch
from training.adapters.jsonl_adapter import JSONLAdapter
from training.dataloaders import build_dataloader
from silhouette_core.training_loop import train as core_train  # reuse your existing loop

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cfg", default="config/train.yaml")
    args = p.parse_args()

    cfg = yaml.safe_load(open(args.cfg, "r", encoding="utf-8"))
    try:
        tok = AutoTokenizer.from_pretrained(cfg["student_model"], use_fast=True)
    except Exception:
        class DummyTokenizer:
            def __call__(self, text, truncation=True, max_length=2048, return_tensors="pt"):
                tokens = text.split()
                ids = list(range(1, len(tokens) + 1))[:max_length]
                input_ids = torch.tensor(ids, dtype=torch.long)
                attn = torch.ones_like(input_ids)
                return {"input_ids": input_ids.unsqueeze(0), "attention_mask": attn.unsqueeze(0)}

        tok = DummyTokenizer()

    adapter = JSONLAdapter(cfg["data"]["path"])
    train_loader = build_dataloader(
        adapter.samples(), tok,
        batch_size=cfg["training"]["batch_size"],
        max_len=cfg["training"]["max_len"]
    )

    core_train(
        model_name=cfg["student_model"],
        train_loader=train_loader,
        output_dir=cfg["output_dir"],
        lora_cfg=cfg.get("lora", {})
    )

if __name__ == "__main__":
    main()
