@echo off
setlocal
cd /d %~dp0\..

if not exist offline\wheels (
  echo offline\wheels not found
  exit /b 2
)
if not exist offline\requirements.lock (
  echo offline\requirements.lock not found
  exit /b 2
)

python -m pip install -U pip
pip install --no-index --find-links offline\wheels -r offline\requirements.lock

echo [OK] Installed from offline wheelhouse
endlocal
exit /b 0
