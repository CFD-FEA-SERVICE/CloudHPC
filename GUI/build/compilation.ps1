# ─────────────────────────────────────────────────────────────────────────────
# Local Windows build helper — run FROM THE REPOSITORY ROOT:
#
#     powershell -ExecutionPolicy Bypass -File GUI\build\compilation.ps1
#
# Builds each enabled app from its PyInstaller spec (GUI\build\SPEC\*.spec).
# Output goes to .\dist\<appName>\ at the repository root — the same layout
# the GitHub Actions workflow and GUI\build\InnoSetup_eseguibile_unico.iss
# expect. Requires: pip install -r GUI\requirements.txt pyinstaller
# ─────────────────────────────────────────────────────────────────────────────

$apps = @(
    # "HVACFlow",
    "bcSnappy",
    # "bestgate",
    "carParks",
    # "tenuFEM",
    "turboApp",
    # "valveFlow",
    "envyFlow",
    # "watAirFlux",
    "fea"
)

foreach ($app in $apps) {
    Write-Host "=== Building $app ===" -ForegroundColor Cyan
    python -m PyInstaller --noconfirm "GUI\build\SPEC\$app.spec"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build FAILED for $app" -ForegroundColor Red
        exit 1
    }
}
Write-Host "All builds completed. Output in .\dist\" -ForegroundColor Green
