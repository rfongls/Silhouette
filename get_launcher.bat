@echo off
set URL=https://github.com/silhouette-ai/silhouette-launcher/releases/latest/download/SilhouetteLauncher.exe
set EXE=SilhouetteLauncher.exe
powershell -Command "Invoke-WebRequest %URL% -OutFile %EXE%"
%EXE%
