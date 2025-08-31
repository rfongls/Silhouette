$Url = "https://github.com/rfongls/Silhouette/releases/latest/download/SilhouetteLauncher.exe"
$ShaUrl = "https://github.com/rfongls/Silhouette/releases/latest/download/SilhouetteLauncher.exe.sha256.txt"
$Exe = "SilhouetteLauncher.exe"
$Sha = "$Exe.sha256.txt"
try {
  Invoke-WebRequest $Url -OutFile $Exe -UseBasicParsing
  Invoke-WebRequest $ShaUrl -OutFile $Sha -UseBasicParsing
} catch {
  Write-Host "[!] Falling back to curl"
  & curl.exe -L -o $Exe $Url
  & curl.exe -L -o $Sha $ShaUrl
}
if (-not (Test-Path $Exe)) { Write-Error "Download failed"; exit 1 }
if (-not (Test-Path $Sha)) { Write-Error "Checksum download failed"; exit 1 }

$expected = Get-Content $Sha | Select-Object -First 1
$actual = (Get-FileHash $Exe -Algorithm SHA256).Hash
if ($expected -ne $actual) { Write-Error "Checksum mismatch"; exit 1 }

Start-Process $Exe
