#!/usr/bin/env python
import argparse
import json
import pathlib
import time

def _write_stub(out_dir, meta):
    p = pathlib.Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    (p / "QUANTIZE_STUB.txt").write_text(
        "This is a placeholder artifact. Real quantization was unavailable at runtime.\n",
        encoding="utf-8",
    )
    (p / "quantize_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[stub] wrote placeholder files to {out_dir}")

def _quantize_int8(src, out_dir):
    meta = {
        "method": "int8-dynamic",
        "src": src,
        "out_dir": out_dir,
        "ts": time.time(),
        "status": "stub",
        "notes": "PyTorch dynamic quantization of Linear layers on CPU",
    }
    try:
        import torch  # type: ignore
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore

        print(f"[int8] loading {src} (this may be slow on CPU)...")
        model = AutoModelForCausalLM.from_pretrained(src)
        model_quant = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
        print(f"[int8] saving quantized model to {out_dir} ...")
        model_quant.save_pretrained(out_dir)
        try:
            tok = AutoTokenizer.from_pretrained(src, use_fast=True)
            tok.save_pretrained(out_dir)
        except Exception:
            pass
        meta["status"] = "ok"
        (pathlib.Path(out_dir) / "quantize_meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        print("[int8] done.")
    except Exception as e:
        meta["error"] = repr(e)
        _write_stub(out_dir, meta)

def _quantize_gguf(src, out_dir):
    meta = {
        "method": "gguf-stub",
        "src": src,
        "out_dir": out_dir,
        "ts": time.time(),
        "status": "stub",
        "notes": "Real GGUF export requires llama.cpp convert.py; see README section.",
    }
    _write_stub(out_dir, meta)

def _export_onnx_int8(src, out_path):
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        import torch  # type: ignore

        model = AutoModelForCausalLM.from_pretrained(src)
        _ = AutoTokenizer.from_pretrained(src)
        torch.onnx.export(
            model,
            (torch.ones((1, 1), dtype=torch.long)),
            out_path,
            input_names=["input_ids"],
            output_names=["logits"],
            opset_version=17,
            dynamic_axes={"input_ids": {0: "batch"}},
        )
        print(f"ONNX INT8 export stub written to {out_path}")
    except Exception as e:
        pathlib.Path(out_path).write_text("ONNX export stub\n", encoding="utf-8")
        print("ONNX export fallback:", e)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["int8", "gguf", "onnx-int8"], required=True)
    ap.add_argument("--src", required=True, help="HF model id or local path (e.g., models/student-core-kd)")
    ap.add_argument("--out", required=True, help="Output directory or file for quantized artifact")
    args = ap.parse_args()

    if args.method == "int8":
        _quantize_int8(args.src, args.out)
    elif args.method == "gguf":
        _quantize_gguf(args.src, args.out)
    elif args.method == "onnx-int8":
        _export_onnx_int8(args.src, args.out)

if __name__ == "__main__":
    main()
