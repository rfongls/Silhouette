import os
import gradio as gr
import subprocess

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL: Persist Hugging Face cache between runs
# Make sure /mnt/data/hf_cache is a mounted volume in your Space
os.environ.setdefault("HF_HOME", "/mnt/data/hf_cache")
os.environ.setdefault("TRANSFORMERS_CACHE", os.environ["HF_HOME"])
# ─────────────────────────────────────────────────────────────────────────────

def run_training():
    # build the accelerate command
    cmd = [
        "accelerate", "launch",
        "--cpu",
        "--num_processes", "1",
        "--num_machines", "1",
        "--mixed_precision", "no",
        "--dynamo_backend", "no",
        # point to your core training script:
        "../training/train_silhouette.py",
        "--config", "../config/train_config.yaml"
    ]

    # stream stdout+stderr
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in process.stdout:
        yield line
    process.wait()

def main():
    with gr.Blocks() as demo:
        gr.Markdown("# Silhouette Trainer")
        output = gr.Textbox(label="Logs", lines=20)
        start = gr.Button("Start Training")
        start.click(run_training, outputs=output)
    demo.launch()

if __name__ == "__main__":
    main()
