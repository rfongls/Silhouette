@echo off
REM Back-compat shim; prefer run.ui.bat instead
setlocal
echo [DEPRECATED] Use run.ui.bat instead. Launching...
call "%~dp0run.ui.bat" %*
endlocal
exit /B %ERRORLEVEL%
