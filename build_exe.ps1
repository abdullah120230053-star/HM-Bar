$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
# Prevent PyInstaller from resolving app DLLs against unrelated desktop runtimes.
$env:Path = (($env:Path -split ';') | Where-Object { $_ -notmatch '[\\/]codex-runtimes[\\/]' }) -join ';'
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python -m PyInstaller --clean --noconfirm --noconsole --onefile `
    --name HM-Bar --collect-all winsdk --collect-all qtawesome `
    --hidden-import winsdk.windows.ui.notifications.management `
    --add-data "config.json;." main.py
if ($LASTEXITCODE -ne 0) { throw "Island build failed ($LASTEXITCODE)." }
& $python -m PyInstaller --clean --noconfirm --noconsole --onefile `
    --name HM-Bar-Settings settings_app.py
if ($LASTEXITCODE -ne 0) { throw "Settings build failed ($LASTEXITCODE)." }
Write-Host "Built HM-Bar and HM-Bar Settings in dist."
