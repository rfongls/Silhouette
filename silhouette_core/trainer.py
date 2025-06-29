# silhouette_core/trainer.py

import argparse
import json
import os

from datasets import load_dataset
from peft import get_peft_model, LoraConfig
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


def train_codex(cfg):
    # 0) Make sure your token is present
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN not found in environment; please add it as a Space secret")

    # 1) Load tokenizer & base model from the correct repo
    tokenizer = AutoTokenizer.from_pretrained(
        cfg["model_name_or_path"],
        token=hf_token,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        cfg["model_name_or_path"],
        device_map="auto",
        torch_dtype=cfg.get("torch_dtype", "auto"),
        token=hf_token,
    )

    # 2) Apply LoRA adapter
    peft_cfg = LoraConfig(
        r=cfg["lora_rank"],
        lora_alpha=cfg["lora_alpha"],
        target_modules=cfg["lora_target_modules"],
        inference_mode=False,
        bias="none",
    )
    model = get_peft_model(base_model, peft_cfg)

    # 3) Build TrainingArguments
    args = TrainingArguments(
        output_dir=cfg["output_dir"],
        per_device_train_batch_size=cfg["train_batch_size"],
        per_device_eval_batch_size=cfg.get("eval_batch_size", cfg["train_batch_size"]),
        num_train_epochs=cfg["num_train_epochs"],
        learning_rate=cfg["learning_rate"],
        logging_steps=cfg.get("logging_steps", 100),
        save_steps=cfg.get("save_steps", 500),
        evaluation_strategy=cfg.get("evaluation_strategy", "steps"),
        eval_steps=cfg.get("eval_steps", 500),
        fp16=cfg.get("mixed_precision", "no").lower() in ("fp16", "16"),
        push_to_hub=False,
        report_to=cfg.get("report_to", "none"),
    )

    # 4) Load JSONL datasets (using the token for any gated files)
    datasets = load_dataset(
        "json",
        data_files={
            "train": cfg["train_file"],
            "validation": cfg["validation_file"],
        },
        token=hf_token,
    )

    # 5) Initialize the 🤗 Trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=datasets["train"],
        eval_dataset=datasets["validation"],
        tokenizer=tokenizer,
    )

    # 6) Run training
    trainer.train()

    # 7) Save the adapter
    os.makedirs(cfg["output_dir"], exist_ok=True)
    model.save_pretrained(cfg["output_dir"])


def main():
    parser = argparse.ArgumentParser(description="Silhouette Core Trainer")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to JSON config file (e.g. training/configs/codex.json)",
    )
    args = parser.parse_args()

    # Load the config JSON
    cfg = json.load(open(args.config, "r"))

    # Dispatch: here only codex is supported
    name = os.path.basename(args.config).lower()
    if "codex" in name:
        train_codex(cfg)
    else:
        raise ValueError(f"Unrecognized training config: {args.config}")


if __name__ == "__main__":
    main()
