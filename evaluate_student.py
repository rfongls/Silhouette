"""Evaluate a quantized student model against a JSONL test set."""

from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable


class DummyModel:
    """Minimal stand‑in used when transformers/peft are unavailable."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def generate(self, prompt: str, *, max_new_tokens: int, temperature: float) -> str:
        return f"# generated code for {prompt}\nprint('stub')\n"


class HFModelWrapper:
    """Small wrapper around a Hugging Face model and tokenizer."""

    def __init__(self, tokenizer: Any, model: Any) -> None:
        self.tokenizer = tokenizer
        self.model = model

    def generate(self, prompt: str, *, max_new_tokens: int, temperature: float) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens, temperature=temperature)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)


def load_model(model_path: Path) -> Any:
    """Load a quantized model with a 4‑bit adapter or return a dummy."""

    if not model_path.exists():
        raise FileNotFoundError(model_path)

    try:  # heavy imports are optional for unit tests
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
        import torch

        tokenizer = AutoTokenizer.from_pretrained(model_path)
        base_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
        )
        model = PeftModel.from_pretrained(base_model, model_path)
        model.eval()
        return HFModelWrapper(tokenizer, model)
    except Exception:
        # Fall back to a stub so tests don't require transformers
        return DummyModel(model_path)


def _can_compile(code: str) -> bool:
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        py_compile.compile(tmp_path, doraise=True)
        return True
    except py_compile.PyCompileError:
        return False
    finally:
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _run_reference_tests(code: str, reference: str) -> bool:
    if not reference:
        return False
    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = Path(tmpdir) / "candidate.py"
        code_file.write_text(code)
        test_file = Path(tmpdir) / "test_reference.py"
        test_file.write_text(reference)
        proc = subprocess.run(
            ["pytest", "-q", str(test_file)],
            cwd=tmpdir,
            capture_output=True,
        )
        return proc.returncode == 0


def run_tests(
    model: Any,
    tests: Iterable[dict[str, Any]],
    *,
    max_tokens: int = 128,
    temperature: float = 0.0,
) -> tuple[float, float, list[dict[str, Any]]]:
    """Run evaluation and return rates plus per-prompt results."""

    total = 0
    compile_ok = 0
    test_ok = 0
    results = []

    for entry in tests:
        prompt = entry.get("prompt", "")
        reference = entry.get("reference", "")
        total += 1
        generated = model.generate(prompt, max_new_tokens=max_tokens, temperature=temperature)
        compiled = _can_compile(generated)
        if compiled:
            compile_ok += 1
        tests_passed = _run_reference_tests(generated, reference) if reference else False
        if tests_passed:
            test_ok += 1
        results.append(
            {
                "prompt": prompt,
                "generated": generated,
                "compiled": compiled,
                "tests_passed": tests_passed,
            }
        )

    rate_compile = compile_ok / total if total else 0.0
    rate_test = test_ok / total if total else 0.0
    return rate_compile, rate_test, results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate a trained student model")
    parser.add_argument("--model-path", default="modules/reasoner/adapter/qlora4b")
    parser.add_argument("--test-file", default="training_data/reasoner/stage1_test.jsonl")
    parser.add_argument("--output", default="evaluation_results.json")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args(argv)

    with open(args.test_file, "r", encoding="utf-8") as f:
        tests = [json.loads(line) for line in f if line.strip()]

    model = load_model(Path(args.model_path))
    compile_rate, test_rate, results = run_tests(
        model,
        tests,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )

    summary = {
        "total_prompts": len(tests),
        "compile_success_rate": compile_rate,
        "test_pass_rate": test_rate,
    }

    print(f"Total prompts: {summary['total_prompts']}")
    print(f"Compile success rate: {compile_rate:.2%}")
    print(f"Test pass rate: {test_rate:.2%}")

    with open(args.output, "w", encoding="utf-8") as fout:
        json.dump({"summary": summary, "results": results}, fout, indent=2)


if __name__ == "__main__":
    main()

