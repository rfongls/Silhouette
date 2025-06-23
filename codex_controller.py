import subprocess
import yaml
import os

def load_next_task(config_path="auto_dev.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

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
    result = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
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
