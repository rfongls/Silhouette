import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import zipfile


class RunIO:
    def __init__(self, out_root: str = "out/security"):
        self.out_root = Path(out_root)
        self._run_dir: Path | None = None

    def new_run_dir(self) -> Path:
        # allow using existing run directory
        if (self.out_root / 'run.json').exists():
            self._run_dir = self.out_root
            return self._run_dir
        ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.out_root / ts
        run_dir.mkdir(parents=True, exist_ok=True)
        self._run_dir = run_dir
        return run_dir

    def current_or_new_run_dir(self) -> Path:
        return self._run_dir if self._run_dir else self.new_run_dir()

    def write_manifest(self, run_dir: Path, meta: dict) -> None:
        manifest = run_dir / "run.json"
        entries = []
        if manifest.exists():
            try:
                entries = json.loads(manifest.read_text())
            except json.JSONDecodeError:
                entries = []
        entries.append(meta)
        manifest.write_text(json.dumps(entries, indent=2))

    @staticmethod
    def sha256sum(path: Path) -> str:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def zip_dir(src: Path, zip_path: Path) -> None:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for file in src.rglob('*'):
                if file.is_file():
                    z.write(file, file.relative_to(src))
