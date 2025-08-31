$Url = "https://github.com/silhouette-ai/silhouette-launcher/releases/latest/download/SilhouetteLauncher.exe"
$Exe = "SilhouetteLauncher.exe"
Invoke-WebRequest $Url -OutFile $Exe
Start-Process $Exe
