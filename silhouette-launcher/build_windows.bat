@echo off
setlocal
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm --onefile --windowed --name SilhouetteLauncher launcher/main.py
echo Built dist\SilhouetteLauncher.exe
