from __future__ import annotations
import sys, traceback
from pathlib import Path
try:
    from PySide6.QtWidgets import (
        QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QComboBox, QCheckBox, QPlainTextEdit, QMessageBox, QLineEdit
    )
    from PySide6.QtCore import Qt, QThread, Signal
except ModuleNotFoundError:  # pragma: no cover - allows tests without PySide6
    QApplication = object  # type: ignore
    QWidget = object  # type: ignore
    QFileDialog = QVBoxLayout = QHBoxLayout = QPushButton = QLabel = QComboBox = QCheckBox = QPlainTextEdit = QMessageBox = QLineEdit = object  # type: ignore
    Qt = QThread = Signal = object  # type: ignore

from .bootstrap import bootstrap

SKILLS = ["fhir","validate","core","runtime","ml","dev","eval","all"]


if hasattr(QWidget, "__mro__") and QWidget is not object:
    class Worker(QThread):
        line = Signal(str)
        done = Signal(bool, str)
        def __init__(self, repo: Path, skill: str, with_hapi: bool):
            super().__init__()
            self.repo = repo; self.skill = skill; self.with_hapi = with_hapi
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
            super().__init__()
            self.setWindowTitle("Silhouette Launcher")
            self.setMinimumWidth(800)

            self.repo_edit = QLineEdit()
            self.browse_btn = QPushButton("Browse…")
            self.skill_combo = QComboBox(); self.skill_combo.addItems(SKILLS)
            self.hapi_chk = QCheckBox("Start local HAPI (Docker)")

            top = QHBoxLayout()
            top.addWidget(QLabel("Repo:"))
            top.addWidget(self.repo_edit, 1)
            top.addWidget(self.browse_btn)

            mid = QHBoxLayout()
            mid.addWidget(QLabel("Skill:"))
            mid.addWidget(self.skill_combo)
            mid.addStretch(1)
            mid.addWidget(self.hapi_chk)

            self.run_btn = QPushButton("Run Setup")
            self.log = QPlainTextEdit(); self.log.setReadOnly(True)

            layout = QVBoxLayout(self)
            layout.addLayout(top); layout.addLayout(mid)
            layout.addWidget(self.run_btn); layout.addWidget(self.log, 1)

            self.browse_btn.clicked.connect(self.pick_repo)
            self.run_btn.clicked.connect(self.start)

            self.worker = None

        def pick_repo(self):
            d = QFileDialog.getExistingDirectory(self, "Select Silhouette Repo Folder", "")
            if d:
                self.repo_edit.setText(d)

        def append_log(self, s: str):
            self.log.appendPlainText(s)

        def start(self):
            path = Path(self.repo_edit.text().strip() or ".").resolve()
            if not path.exists():
                QMessageBox.critical(self, "Error", "Folder does not exist")
                return
            self.log.clear()
            self.append_log(f"Repo: {path}")
            self.run_btn.setEnabled(False)

            skill = self.skill_combo.currentText()
            with_hapi = self.hapi_chk.isChecked()
            self.worker = Worker(path, skill, with_hapi)
            self.worker.line.connect(self.append_log, Qt.QueuedConnection)
            self.worker.done.connect(self.on_done, Qt.QueuedConnection)
            self.worker.start()

        def on_done(self, ok: bool, msg: str):
            self.run_btn.setEnabled(True)
            if ok:
                QMessageBox.information(self, "Done", "Setup complete.")
            else:
                QMessageBox.critical(self, "Failed", f"Setup failed:\n{msg}")

    def main():
        app = QApplication(sys.argv)  # type: ignore
        w = Launcher(); w.show()
        sys.exit(app.exec())
else:
    class Worker:  # minimal stubs when PySide6 missing
        pass

    class Launcher:  # pragma: no cover - stub for import time
        pass

    def main():  # pragma: no cover
        raise ModuleNotFoundError("PySide6 is required to run the GUI")
