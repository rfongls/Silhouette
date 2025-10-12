@echo off
setlocal ENABLEDELAYEDEXPANSION

REM --- Find a Python to run the installer ---
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  set PY=python
) else (
  where py >nul 2>&1
  if %ERRORLEVEL% EQU 0 (
    set PY=py -3
  ) else (
    echo [!] Python not found in PATH. Please install Python 3.x or run:
    echo     python scripts\install_shortcuts.py
    exit /b 1
  )
)

REM --- Move to repo root (this .bat lives in scripts\) ---
pushd %~dp0\..
%PY% scripts\install_shortcuts.py %*
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
