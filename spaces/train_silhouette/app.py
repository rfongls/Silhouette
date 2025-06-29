import gradio as gr
import subprocess


def run_training():
    process = subprocess.Popen([
        'python', 'train_silhouette.py'],
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


if __name__ == '__main__':
    main()
