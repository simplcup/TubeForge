$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    python -m PyInstaller --noconfirm --clean TubeForge.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
    $exe = Join-Path $PSScriptRoot "dist\TubeForge.exe"
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "`nBuilt $exe ($size MB)" -ForegroundColor Green
} finally {
    Pop-Location
}
