from pathlib import Path
import sys

# Ensure repo root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from training import train_silhouette as core


def main():
    config = ROOT / 'config' / 'train_config.yaml'
    core.main(["--config", str(config)])


if __name__ == "__main__":
    main()
