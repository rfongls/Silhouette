@echo off
setlocal
set URL=https://github.com/silhouette-ai/Silhouette/releases/latest/download/SilhouetteLauncher.exe
set EXE=SilhouetteLauncher.exe

:: Try PowerShell, else curl
powershell -Command "Invoke-WebRequest %URL% -OutFile %EXE%" || curl -L -o %EXE% %URL%
if not exist %EXE% (
  echo [x] Download failed
  exit /b 1
)

:: (Optional) verify checksum if you publish SHA256.txt next to the EXE
:: certutil -hashfile %EXE% SHA256

%EXE%
