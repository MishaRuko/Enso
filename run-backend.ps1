param(
  [int]$Port = 8111
)

$ErrorActionPreference = "Stop"

# Always run from repo root so backend.src.main imports resolve correctly
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

Write-Host "Starting backend on port $Port"

# Use venv Python directly — avoids system Python (anaconda, etc.) being picked up
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Error ".venv not found. Run: python -m venv .venv && pip install -r requirements.txt"
  exit 1
}

# Kill anything already on this port (stale server from a previous run)
$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($existing) {
  $existing.OwningProcess | Select-Object -Unique | ForEach-Object {
    Write-Host "Killing stale process on port $Port (PID $_)"
    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep 2
}

$env:PYTHONIOENCODING = "utf-8"
# Store .pyc cache outside OneDrive — prevents timestamp corruption from sync
$env:PYTHONPYCACHEPREFIX = "$env:TEMP\homedesigner-pycache"

& $python -m uvicorn backend.src.main:app --reload --host 127.0.0.1 --port $Port
