FROM ghcr.io/huggingface/transformers-pytorch-gpu:latest

COPY . /workspace
WORKDIR /workspace

RUN pip install --no-cache-dir -r requirements-dev.txt \
    && pip install accelerate bitsandbytes peft

# (Optional) bake in accelerate config
COPY accelerate_config.yaml /workspace/

CMD accelerate launch training/train.py \
    --config training/configs/codex.json
