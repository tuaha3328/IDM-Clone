$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Create .venv and install requirements.txt before building. See README.md."
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name IDM-Clone `
    --collect-all yt_dlp `
    --collect-all imageio_ffmpeg.binaries `
    main.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host "Built dist\IDM-Clone.exe"
