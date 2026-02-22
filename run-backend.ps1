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

# Clear __pycache__ directories — OneDrive corrupts file timestamps which causes
# Python to load stale .pyc bytecode even when source files have changed
Write-Host "Clearing __pycache__ to avoid stale bytecode..."
Get-ChildItem -Path $repoRoot -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Kill ALL python.exe processes — uvicorn --reload spawns child processes that
# inherit the socket, so killing by port alone misses them. On this dev machine
# only our server uses Python, so this is safe.
Write-Host "Killing all Python processes to clear stale servers..."
Get-Process -Name python,pythonw -ErrorAction SilentlyContinue |
  Stop-Process -Force -ErrorAction SilentlyContinue

# Also kill any remaining holder of the specific port
$conns = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($conns) {
  $stalePids = $conns.OwningProcess | Sort-Object -Unique
  foreach ($stalePid in $stalePids) {
    Write-Host "Killing stale process PID $stalePid on port $Port"
    Stop-Process -Id $stalePid -Force -ErrorAction SilentlyContinue
  }
}
Start-Sleep 3

$env:PYTHONIOENCODING = "utf-8"
# Use a fresh unique cache dir each start — guarantees Python always reads source files
$env:PYTHONPYCACHEPREFIX = "$env:TEMP\hd-pycache-$(Get-Date -Format 'yyyyMMddHHmmss')"

& $python -m uvicorn backend.src.main:app --reload --host 127.0.0.1 --port $Port
