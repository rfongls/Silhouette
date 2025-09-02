import argparse
from pathlib import Path

REPORT_DIR = Path("reports")


def summarize_session(log_file: Path) -> str:
    lines = log_file.read_text(encoding="utf-8").splitlines()
    summary = f"lines={len(lines)}"
    return summary


def write_summary(log_file: Path, report_dir: Path = REPORT_DIR) -> Path:
    report_dir.mkdir(exist_ok=True)
    summary = summarize_session(log_file)
    out = report_dir / f"{log_file.stem}_summary.txt"
    out.write_text(summary, encoding="utf-8")
    return out


def latest_log(log_dir: Path = Path("logs")) -> Path | None:
    files = sorted(log_dir.glob("silhouette_session_*.txt"))
    return files[-1] if files else None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Summarize session log")
    parser.add_argument("--log", type=Path, default=None)
    args = parser.parse_args(argv)

    path = args.log or latest_log()
    if not path or not path.exists():
        print("No session log found")
        return
    out = write_summary(path)
    print(f"Session summary saved to {out}")


if __name__ == "__main__":
    main()
