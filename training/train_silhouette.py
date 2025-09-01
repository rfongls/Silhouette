import argparse
import yaml
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig
from pathlib import Path
import os


def main(argv=None):
    parser = argparse.ArgumentParser(description="Train Silhouette model")
    parser.add_argument("--config", type=str, default="config/train_config.yaml")
    args = parser.parse_args(argv)

    cfg_path = Path(args.config)
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    hf_token = os.environ.get("HF_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained(cfg["model_name_or_path"], token=hf_token)
    base_model = AutoModelForCausalLM.from_pretrained(cfg["model_name_or_path"], device_map="auto", token=hf_token)

    lora_cfg = LoraConfig(
        r=cfg.get("lora_rank", 8),
        lora_alpha=cfg.get("lora_alpha", 16),
        target_modules=cfg.get("lora_target_modules", ["q_proj", "v_proj"]),
        bias="none",
        inference_mode=False,
    )
    model = get_peft_model(base_model, lora_cfg)

    ds = load_dataset(
        "json",
        data_files={"train": cfg["train_file"], "validation": cfg["validation_file"]},
    )

    training_args = TrainingArguments(
        output_dir=cfg["output_dir"],
        per_device_train_batch_size=cfg["train_batch_size"],
        per_device_eval_batch_size=cfg.get("eval_batch_size", cfg["train_batch_size"]),
        num_train_epochs=cfg["num_train_epochs"],
        learning_rate=cfg["learning_rate"],
        logging_steps=cfg.get("logging_steps", 50),
        save_steps=cfg.get("save_steps", 500),
        evaluation_strategy=cfg.get("evaluation_strategy", "steps"),
        eval_steps=cfg.get("eval_steps", 500),
        fp16=cfg.get("mixed_precision", "no") in ("fp16", "16"),
        push_to_hub=False,
        report_to=cfg.get("report_to", "none"),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        tokenizer=tokenizer,
    )

    trainer.train()

    Path(cfg["output_dir"]).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(cfg["output_dir"])


if __name__ == "__main__":
    main()
