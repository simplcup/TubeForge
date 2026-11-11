$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $core = Get-Content (Join-Path $PSScriptRoot "app\core.py") -Raw
    $match = [regex]::Match($core, 'APP_VERSION\s*=\s*"([^"]+)"')
    if (-not $match.Success) { throw "Could not read APP_VERSION from app\core.py" }
    $version = $match.Groups[1].Value

    $exe = Join-Path $PSScriptRoot "dist\TubeForge.exe"
    if (-not (Test-Path $exe)) {
        throw "dist\TubeForge.exe is missing. Run .\build.ps1 first."
    }

    $isccCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }

    $iscc = $isccCandidates | Select-Object -First 1
    if (-not $iscc) {
        Write-Host "Inno Setup 6 not found; installing it with winget..." -ForegroundColor Yellow
        winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements --silent --disable-interactivity
        if ($LASTEXITCODE -ne 0) { throw "Could not install Inno Setup 6." }
        $iscc = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
        ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    }
    if (-not $iscc) { throw "ISCC.exe was not found after installing Inno Setup." }

    & $iscc "/DMyAppVersion=$version" (Join-Path $PSScriptRoot "installer\TubeForge.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

    $setup = Join-Path $PSScriptRoot "dist\TubeForge-Setup-$version.exe"
    $size = [math]::Round((Get-Item $setup).Length / 1MB, 1)
    Write-Host "`nBuilt $setup ($size MB)" -ForegroundColor Green
} finally {
    Pop-Location
}
