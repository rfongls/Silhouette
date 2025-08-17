import argparse
import yaml
import json
from transformers import AutoTokenizer
from training.adapters.jsonl_adapter import JSONLAdapter
from training.dataloaders import build_dataloader
from silhouette_core.distiller import distill as core_kd  # reuse your existing KD

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cfg", default="config/train.yaml")
    args = p.parse_args()

    cfg = yaml.safe_load(open(args.cfg, "r", encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(cfg["student_model"], use_fast=True)

    adapter = JSONLAdapter(cfg["data"]["path"])
    train_loader = build_dataloader(
        adapter.samples(), tok,
        batch_size=cfg["training"]["batch_size"],
        max_len=cfg["training"]["max_len"]
    )

    teacher_outputs = None
    if cfg.get("teacher_outputs"):
        with open(cfg["teacher_outputs"], "r", encoding="utf-8") as fh:
            teacher_outputs = [json.loads(line) for line in fh if line.strip()]

    core_kd(
        student_model=cfg["student_model"],
        train_loader=train_loader,
        teacher_model=cfg.get("teacher_model"),
        teacher_outputs=teacher_outputs,
        output_dir=cfg["output_dir"],
        lora_cfg=cfg.get("lora", {})
    )

if __name__ == "__main__":
    main()
