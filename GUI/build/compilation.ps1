# ─────────────────────────────────────────────────────────────────────────────
# Local Windows build helper — run FROM THE REPOSITORY ROOT:
#
#     powershell -ExecutionPolicy Bypass -File GUI\build\compilation.ps1
#
# IMPORTANT: must be run inside a conda environment with pythonocc-core,
# because OCC (the CAD/GEO tab) is only distributed on conda-forge, not PyPI.
# One-time environment setup:
#
#     conda create -n cloudhpc-build python=3.11
#     conda activate cloudhpc-build
#     conda install -c conda-forge pythonocc-core
#     pip install -r GUI\requirements.txt pyinstaller
#
# Builds each enabled app from its PyInstaller spec (GUI\build\SPEC\*.spec).
# Output goes to .\dist\<appName>\ at the repository root — the same layout
# the GitHub Actions workflow and GUI\build\InnoSetup_eseguibile_unico.iss
# expect.
# ─────────────────────────────────────────────────────────────────────────────

# Guard: refuse to build OCC-less apps by mistake
python -c "import OCC.Core.STEPControl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pythonocc-core not importable in this environment." -ForegroundColor Red
    Write-Host "Activate the conda build env first (see header of this script)." -ForegroundColor Red
    exit 1
}

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
