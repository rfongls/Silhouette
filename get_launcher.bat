@echo off
setlocal
set URL=https://github.com/rfongls/Silhouette/releases/latest/download/SilhouetteLauncher.exe
set EXE=SilhouetteLauncher.exe
set SHA_URL=https://github.com/rfongls/Silhouette/releases/latest/download/SilhouetteLauncher.exe.sha256.txt
set SHA=%EXE%.sha256.txt

:: Try PowerShell, else curl
powershell -Command "Invoke-WebRequest %URL% -OutFile %EXE%" || curl -L -o %EXE% %URL%
powershell -Command "Invoke-WebRequest %SHA_URL% -OutFile %SHA%" || curl -L -o %SHA% %SHA_URL%
if not exist %EXE% (
  echo [x] Download failed
  exit /b 1
)
if not exist %SHA% (
  echo [x] Checksum download failed
  exit /b 1
)
for /f %%i in (%SHA%) do set EXPECTED=%%i
for /f %%i in ('powershell -NoP -C "(Get-FileHash ''%EXE%'' -Algorithm SHA256).Hash"') do set ACTUAL=%%i
if /I not "%EXPECTED%"=="%ACTUAL%" (
  echo [x] Checksum mismatch
  exit /b 1
)

%EXE%
