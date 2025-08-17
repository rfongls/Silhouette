import argparse
import yaml
from transformers import AutoTokenizer
from training.adapters.jsonl_adapter import JSONLAdapter
from training.dataloaders import build_dataloader
from silhouette_core.training_loop import train as core_train  # reuse your existing loop

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

    core_train(
        model_name=cfg["student_model"],
        train_loader=train_loader,
        output_dir=cfg["output_dir"],
        lora_cfg=cfg.get("lora", {})
    )

if __name__ == "__main__":
    main()
