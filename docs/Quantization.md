# Quantization

- Library: `silhouette_core/quantize_models.py`
- Script: `scripts/quantize.py`

## Supported Backends & Options
- `int8` – dynamic quantization of Linear layers on CPU
- `gguf` – stubbed GGUF export (requires external tooling)
- `onnx-int8` – ONNX graph export stub

## Examples
```bash
# Convert distilled embeddings to a compact file
python -m silhouette_core.quantize_models --distillate distillate.json --output embeddings.tflite

# Quantize a model to int8
python scripts/quantize.py --method int8 --src models/student-core-kd --out artifacts/int8

# Export an ONNX int8 model
python scripts/quantize.py --method onnx-int8 --src models/student-core-kd --out model.onnx
```
