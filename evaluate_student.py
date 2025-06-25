import argparse
import json
from pathlib import Path


class DummyModel:
    """Placeholder model that echoes the prompt."""

    def __init__(self, adapter: Path) -> None:
        self.adapter = adapter

    def generate(self, prompt: str) -> str:
        return f"# solution for {prompt}\n"


def load_model(adapter_dir: Path) -> DummyModel:
    if not adapter_dir.exists():
        raise FileNotFoundError(adapter_dir)
    return DummyModel(adapter_dir)


def run_tests(model: DummyModel, tests: list[dict]) -> tuple[float, float]:
    total = len(tests)
    compile_ok = 0
    test_ok = 0
    for entry in tests:
        prompt = entry.get("prompt", "")
        reference = entry.get("reference_code", "")
        candidate = model.generate(prompt)
        try:
            compile(candidate, "<string>", "exec")
            compile_ok += 1
            exec_env = {}
            exec(candidate, exec_env)
            if reference:
                exec(reference, exec_env)
            test_ok += 1
        except Exception:
            pass
    if total == 0:
        return 0.0, 0.0
    return compile_ok / total, test_ok / total


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate student adapter")
    parser.add_argument("--adapter", default="modules/reasoner/adapter/qlora4b")
    parser.add_argument("--test-file", default="training_data/reasoner/stage1_sample.jsonl")
    args = parser.parse_args(argv)

    model = load_model(Path(args.adapter))
    tests = []
    with open(args.test_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                tests.append(json.loads(line))
    compile_rate, test_rate = run_tests(model, tests)
    print(f"Compile success rate: {compile_rate:.2%}")
    print(f"Test pass rate: {test_rate:.2%}")


if __name__ == "__main__":
    main()
