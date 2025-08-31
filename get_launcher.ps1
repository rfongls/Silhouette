$Url = "https://github.com/silhouette-ai/Silhouette/releases/latest/download/SilhouetteLauncher.exe"
$Exe = "SilhouetteLauncher.exe"
try {
  Invoke-WebRequest $Url -OutFile $Exe -UseBasicParsing
} catch {
  Write-Host "[!] Falling back to curl"
  & curl.exe -L -o $Exe $Url
}
if (-not (Test-Path $Exe)) { Write-Error "Download failed"; exit 1 }

# (Optional) checksum verification (publish checksums to your release)
# Get-FileHash $Exe -Algorithm SHA256

Start-Process $Exe
