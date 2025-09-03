@echo off
setlocal
cd /d %~dp0\..

if not exist offline\requirements.lock (
  echo offline\requirements.lock not found
  exit /b 2
)

mkdir offline\wheels 2>nul
python -m pip install -U pip
pip download -d offline\wheels -r offline\requirements.lock

echo [OK] Wheels saved to offline\wheels
for %%F in (offline\wheels\*.whl) do set LAST=%%F
dir /b offline\wheels
endlocal
exit /b 0
