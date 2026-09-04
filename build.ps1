$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\pyinstaller.exe)) {
    .venv\Scripts\python -m pip install -r requirements.txt
}

Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location

.venv\Scripts\pyinstaller app.spec --noconfirm --distpath release --workpath build
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "构建完成: release\yt-dlp下载器\yt-dlp下载器.exe"
