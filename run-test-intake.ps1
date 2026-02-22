param(
  [int]$Port = 8111
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$base = "http://127.0.0.1:$Port"

Write-Host "Testing intake flow on $base"

function PostJson($url, $obj) {
  return Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body ($obj | ConvertTo-Json -Depth 10)
}

# 1) Create session
$sessionResp = PostJson "$base/session/new" @{}
$sessionId = $sessionResp.session_id

Write-Host "session_id = $sessionId"

# 2) Turn (fallback text intake)
$turnBody = @{
  session_id = $sessionId
  user_text  = "Budget 5000 EUR, style modern minimalist, rooms living room and bedroom, must haves sofa and desk."
}
$turnResp = PostJson "$base/voice_intake/turn" $turnBody

Write-Host ""
Write-Host "Turn response:"
$turnResp | ConvertTo-Json -Depth 10

# 3) Finalize (miro creation or stub)
$finalResp = PostJson "$base/voice_intake/finalize" @{ session_id = $sessionId }

Write-Host ""
Write-Host "Finalize response:"
$finalResp | ConvertTo-Json -Depth 10

# Try to print miro url with common keys
$miroUrl = $null
if ($finalResp.miro_board_url) { $miroUrl = $finalResp.miro_board_url }
elseif ($finalResp.miro -and $finalResp.miro.board_url) { $miroUrl = $finalResp.miro.board_url }

if ($miroUrl) {
  Write-Host ""
  Write-Host "MIRO URL:"
  Write-Host $miroUrl
} else {
  Write-Host ""
  Write-Host "No miro url field found in finalize response. Check response JSON above."
}

Write-Host ""
Write-Host "Done"
