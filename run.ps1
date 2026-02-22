# Run backend and frontend simultaneously (Windows PowerShell)
# Ctrl+C stops both

$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting backend  -> http://localhost:8100"
Write-Host "Starting frontend -> http://localhost:3000"
Write-Host ""

# --- Kill stale processes on ports ---
function Kill-Port($port) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connections) {
        $connections | ForEach-Object {
            try {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            } catch {}
        }
    }
}

Kill-Port 8100
Kill-Port 3000

# --- Start backend ---
$backend = Start-Process powershell -PassThru -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT\backend'; uv run --project '$ROOT' uvicorn src.main:app --reload --host 0.0.0.0 --port 8100"
)

# --- Start frontend ---
$frontend = Start-Process powershell -PassThru -WindowStyle Normal -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT\frontend\designer-next'; pnpm dev"
)

Write-Host "Backend PID : $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host ""
Write-Host "Press Ctrl+C to stop both..."

try {
    while ($true) {
        Start-Sleep -Seconds 1
        if ($backend.HasExited -or $frontend.HasExited) {
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping..."
    if (!$backend.HasExited) { Stop-Process -Id $backend.Id -Force }
    if (!$frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
}
