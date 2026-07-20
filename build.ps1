# Build SimsTracker.exe — but only if the code actually works.
#
# Usage:
#   .\build.ps1              full build with all checks
#   .\build.ps1 -SkipTests   skip the test suite (faster, less safe)
#
# Every check here exists because something broke without it. Don't
# comment them out; use -SkipTests if you're in a hurry.

param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Assert-LastExit {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) {
        Write-Host $Message -ForegroundColor Red
        exit 1
    }
}

# 1. Stop any running tracker
# Windows won't let PyInstaller overwrite an .exe that's still running, and
# watch mode has no window, so there's usually one running you forgot about.
Write-Host "Stopping any running tracker..." -ForegroundColor Cyan
Get-Process SimsTracker -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

# 2. Compile
# Catches syntax errors. PyInstaller silently omits modules that fail to
# compile, producing a binary that's broken in a very confusing way.
Write-Host "Compiling..." -ForegroundColor Cyan
python -m compileall -q simstracker
Assert-LastExit "Syntax errors - fix before building."

# 3. Smoke test
# compileall won't catch a bad import or a crash on startup. This will.
Write-Host "Smoke test..." -ForegroundColor Cyan
python sims_tracker.py --version
Assert-LastExit "App failed to start - don't ship this."

# 4. Tests
if (-not $SkipTests) {
    Write-Host "Running tests..." -ForegroundColor Cyan
    python -m unittest discover -s tests
    Assert-LastExit "Tests failed."
} else {
    Write-Host "Skipping tests (-SkipTests)." -ForegroundColor Yellow
}

# 5. Clear the cache
# The .spec file matters as much as build/: a stale one takes precedence
# over your command-line flags and carries the old analysis with it.
Write-Host "Clearing build cache..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item -Force *.spec -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 6. Build
# --collect-submodules bundles every module in the package regardless of
# what PyInstaller's import scanner concluded.
Write-Host "Building..." -ForegroundColor Cyan
pyinstaller --onefile --noconsole `
            --collect-submodules simstracker `
            --name SimsTracker sims_tracker.py
Assert-LastExit "PyInstaller failed."

# 7. Verify the output exists
$exe = "dist\SimsTracker.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Build reported success but $exe is missing." -ForegroundColor Red
    exit 1
}

$size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "Done: $exe ($size MB)" -ForegroundColor Green
Write-Host "Test it with: .\$exe" -ForegroundColor Gray