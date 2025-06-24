import subprocess
import os
import sys

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML may not be installed
    yaml = None

def _fallback_load(config_path: str) -> dict:
    """Parse a tiny subset of YAML used by auto_dev.yaml."""
    config: dict[str, object] = {"generate": []}
    with open(config_path, "r") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line or line.lstrip().startswith("#"):
            i += 1
            continue

        if line.startswith("generate:"):
            i += 1
            while i < len(lines) and lines[i].startswith("  -"):
                item: dict[str, str] = {}
                first = lines[i].strip()
                if "file:" in first:
                    item["file"] = first.split("file:", 1)[1].strip()
                i += 1
                while i < len(lines) and lines[i].startswith("    "):
                    sub = lines[i].strip()
                    if ":" in sub:
                        k, v = sub.split(":", 1)
                        item[k.strip()] = v.strip().strip('"')
                    i += 1
                config["generate"].append(item)
            continue

        if line.startswith("jobs:"):
            break

        if ":" in line:
            key, value = line.split(":", 1)
            config[key.strip()] = value.strip()

        i += 1

    return config


def load_next_task(config_path: str = "auto_dev.yaml") -> dict:
    """Load the next Codex task without requiring PyYAML."""
    if yaml:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return _fallback_load(config_path)

def generate_code(task):
    for item in task["generate"]:
        path = item["file"]
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(f"# TODO: Implement {item['description']}")
            print(f"Generated: {path}")
        else:
            print(f"Skipped: {path} already exists")

def run_tests():
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], capture_output=True, text=True)
    print("TEST RESULTS:")
    print(result.stdout)
    if result.returncode != 0:
        print("❌ Tests failed")
    else:
        print("✅ All tests passed")

def update_status(filename):
    print(f"Task completed: {filename}")

if __name__ == "__main__":
    task = load_next_task()
    generate_code(task)
    run_tests()
    update_status(task["generate"][0]["file"])
