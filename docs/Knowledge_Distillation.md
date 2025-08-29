# Knowledge Distillation (`silhouette_core/distiller.py`)

## Overview
Summaries and embeddings are extracted from `memory.jsonl` and persona files.
A placeholder KD routine (`distill_kd`) is provided for downstream training.

## Interfaces
- `distill(persona, memory, config) -> dict`
  - Reads `config/distillation.yml` for `summary_length` and `quantization_bits`.
  - Returns persona text, a memory summary, and quantized embeddings.
- `distill_kd(student_model, train_loader, teacher_model=None, teacher_outputs=None, output_dir, lora_cfg=None)`
  - Creates `distilled.txt` in the output directory; acts as a stub for real KD.

The module can also be invoked as a script:
```bash
python -m silhouette_core.distiller --persona persona.dsl --memory memory.jsonl \
    --config config/distillation.yml --output distillate.json
```

## Workflows
1. Prepare `persona.dsl` and `memory.jsonl`.
2. Run `distiller.py` to generate `distillate.json`.
3. Quantize embeddings with `python -m silhouette_core.quantize_models --distillate distillate.json --output embeddings.tflite`.
