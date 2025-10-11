@echo off
setlocal ENABLEDELAYEDEXPANSION

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  set PY=python
) else (
  where py >nul 2>&1
  if %ERRORLEVEL% EQU 0 (
    set PY=py -3
  ) else (
    echo [!] Python not found in PATH. Please install Python 3.x or run:
    echo     python scripts\uninstall_shortcuts.py
    exit /b 1
  )
)

pushd %~dp0\..
%PY% scripts\uninstall_shortcuts.py %*
set ERR=%ERRORLEVEL%
popd
exit /b %ERR%
