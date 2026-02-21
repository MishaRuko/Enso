param(
  [int]$Port = 8111
)

$ErrorActionPreference = "Stop"

Write-Host "Starting backend on port $Port"

# Optional: activate venv if you use one
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
  Write-Host "Activating .venv"
  . .\.venv\Scripts\Activate.ps1
}

# Move to repo root if script launched elsewhere
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

# Check if port is already used
$inUse = netstat -aon | Select-String ":$Port\s+LISTENING"
if ($inUse) {
  Write-Host "Port $Port is already in use. Details:"
  $inUse | ForEach-Object { Write-Host $_ }
  Write-Host "Pick another port: .\run-backend.ps1 -Port 8112"
  exit 1
}

# Start server
python -m uvicorn backend.src.main:app --reload --host 127.0.0.1 --port $Port
