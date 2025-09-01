from __future__ import annotations
import sys, argparse, importlib.util, traceback
from pathlib import Path

GUI_AVAILABLE = importlib.util.find_spec("PySide6") is not None


def run_cli(repo: Path, skill: str, with_hapi: bool) -> int:
    from .bootstrap import bootstrap
    def on_line(s: str): print(s, flush=True)
    try:
        bootstrap(repo, skill, with_hapi, on_line)
        return 0
    except Exception as e:
        print(f"[!] {e}", file=sys.stderr)
        return 1


def run_gui() -> int:
    if not GUI_AVAILABLE:
        print("[!] PySide6 not installed; use --cli or install PySide6>=6.6", file=sys.stderr)
        return 2

    from PySide6.QtWidgets import (
        QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QComboBox, QCheckBox, QPlainTextEdit, QMessageBox, QLineEdit
    )
    from PySide6.QtCore import Qt, QThread, Signal
    from .bootstrap import bootstrap

    SKILLS = ["fhir","validate","core","runtime","ml","dev","eval","all"]

    class Worker(QThread):
        line = Signal(str); done = Signal(bool, str)
        def __init__(self, repo: Path, skill: str, with_hapi: bool):
            super().__init__(); self.repo=repo; self.skill=skill; self.with_hapi=with_hapi
        def run(self):
            ok, msg = True, "OK"
            try:
                def on_line(s: str): self.line.emit(s)
                bootstrap(self.repo, self.skill, self.with_hapi, on_line)
            except Exception as e:
                ok, msg = False, f"{e}"
                self.line.emit("[!] " + "".join(traceback.format_exception_only(type(e), e)).strip())
            self.done.emit(ok, msg)

    class Launcher(QWidget):
        def __init__(self):
            super().__init__(); self.setWindowTitle("Silhouette Launcher"); self.setMinimumWidth(800)
            self.repo_edit = QLineEdit(); self.browse_btn = QPushButton("Browse…")
            self.skill_combo = QComboBox(); self.skill_combo.addItems(SKILLS)
            self.hapi_chk = QCheckBox("Start local HAPI (Docker)")
            top = QHBoxLayout(); top.addWidget(QLabel("Repo:")); top.addWidget(self.repo_edit,1); top.addWidget(self.browse_btn)
            mid = QHBoxLayout(); mid.addWidget(QLabel("Skill:")); mid.addWidget(self.skill_combo); mid.addStretch(1); mid.addWidget(self.hapi_chk)
            self.run_btn = QPushButton("Run Setup"); self.log = QPlainTextEdit(); self.log.setReadOnly(True)
            lay = QVBoxLayout(self); lay.addLayout(top); lay.addLayout(mid); lay.addWidget(self.run_btn); lay.addWidget(self.log,1)
            self.browse_btn.clicked.connect(self.pick_repo); self.run_btn.clicked.connect(self.start)
            self.worker=None
        def pick_repo(self):
            d = QFileDialog.getExistingDirectory(self, "Select Silhouette Repo Folder", "")
            if d: self.repo_edit.setText(d)
        def append_log(self, s: str): self.log.appendPlainText(s)
        def start(self):
            path = Path(self.repo_edit.text().strip() or ".").resolve()
            if not path.exists(): QMessageBox.critical(self,"Error","Folder does not exist"); return
            self.log.clear(); self.append_log(f"Repo: {path}"); self.run_btn.setEnabled(False)
            skill = self.skill_combo.currentText(); with_hapi = self.hapi_chk.isChecked()
            self.worker = Worker(path, skill, with_hapi)
            self.worker.line.connect(self.append_log); self.worker.done.connect(self.on_done); self.worker.start()
        def on_done(self, ok: bool, msg: str):
            self.run_btn.setEnabled(True)
            if ok: QMessageBox.information(self,"Done","Setup complete.")
            else: QMessageBox.critical(self,"Failed",f"Setup failed:\n{msg}")

    app = QApplication(sys.argv); w=Launcher(); w.show(); return app.exec()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Silhouette Launcher")
    p.add_argument("--cli", action="store_true", help="Run in CLI (headless) mode")
    p.add_argument("--repo", type=Path, default=Path("."), help="Path to Silhouette repo")
    p.add_argument("--skill", default="fhir",
                   choices=["fhir","validate","core","runtime","ml","dev","eval","all"])
    p.add_argument("--with-hapi", action="store_true", help="Start local HAPI (Docker)")
    args = p.parse_args(argv)
    return run_cli(args.repo.resolve(), args.skill, args.with_hapi) if (args.cli or not GUI_AVAILABLE) else run_gui()

if __name__ == "__main__":
    raise SystemExit(main())
