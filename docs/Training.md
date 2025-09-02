# Training (`training/`)

- SFT/KD adapters
- Datasets & configs
- Alignment kernel handoff docs: [alignment_kernel/](./alignment_kernel/)

## Usage
```bash
# Supervised fine-tuning
python -m silhouette_core.cli train --cfg config/train.yaml --mode sft

# Knowledge distillation
python -m silhouette_core.cli train --cfg config/train.yaml --mode kd
```
`config/train.yaml` specifies the `student_model`, optional `teacher_model` or `teacher_outputs`, LoRA settings, `data_mixes`, and `output_dir`. Adapters such as `JSONLAdapter` and `FileFenceAdapter` load training samples; see `training/adapters/`.
