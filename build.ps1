# Build SimsTracker.exe, but only if the code actually compiles.
$ErrorActionPreference = "Stop"

Write-Host "Compiling..." -ForegroundColor Cyan
python -m compileall simstracker
if ($LASTEXITCODE -ne 0) { Write-Host "Syntax errors - fix before building." -ForegroundColor Red; exit 1 }

# Write-Host "Smoke test..." -ForegroundColor Cyan
# python sims_tracker.py --version
# if ($LASTEXITCODE -ne 0) { Write-Host "App failed to start." -ForegroundColor Red; exit 1 }

# Write-Host "Running tests..." -ForegroundColor Cyan
# python -m unittest discover -s tests
# if ($LASTEXITCODE -ne 0) { Write-Host "Tests failed." -ForegroundColor Red; exit 1 }

Write-Host "Building..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
pyinstaller --onefile --noconsole --name SimsTracker sims_tracker.py
Write-Host "Done: dist\SimsTracker.exe" -ForegroundColor Green