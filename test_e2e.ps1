param()
# End-to-end test: voice intake -> Miro board generation
# Usage: powershell -ExecutionPolicy Bypass -File test_e2e.ps1

$BASE = "http://localhost:8100"
$ErrorActionPreference = "Stop"

function Step([string]$n, [string]$label) {
    Write-Host ""
    Write-Host "[$n] $label" -ForegroundColor Cyan
}
function Ok([string]$msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Info([string]$msg) { Write-Host "    $msg" }
function Fail([string]$msg) { Write-Host "    FAIL: $msg" -ForegroundColor Red; exit 1 }

function Call-Api([string]$Method, [string]$Path, [hashtable]$Body = $null) {
    $params = @{ Uri = "$BASE$Path"; Method = $Method; ContentType = "application/json" }
    if ($Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10) }
    return Invoke-RestMethod @params
}

# 1. Health
Step "1" "Health check"
$h = Call-Api "GET" "/health"
if ($h.status -ne "ok") { Fail "Expected status=ok, got $($h.status)" }
Ok $($h | ConvertTo-Json -Compress)

# 2. Session
Step "2" "Create in-memory voice session"
$s = Call-Api "POST" "/session/new"
$sid = $s.session_id
if (-not $sid) { Fail "No session_id returned" }
Ok "session_id=$sid"

# 3. Turn 1
Step "3" "Voice intake turn 1: room, style, budget"
$t1 = Call-Api "POST" "/voice_intake/turn" @{
    session_id = $sid
    user_text  = "I want to redo my living room. Scandinavian minimalist style with warm wood tones. Budget around 3500 euros."
}
$snip = $t1.assistant_text.Substring(0, [Math]::Min(120, $t1.assistant_text.Length))
Info "AI: $snip..."
Info "rooms_priority : $($t1.brief.rooms_priority -join ', ')"
Info "style          : $($t1.brief.style -join ', ')"
Info "budget         : $($t1.brief.budget)"
Info "missing fields : $($t1.missing_fields -join ', ')"
if (-not $t1.brief.rooms_priority) { Fail "rooms_priority not extracted" }

# 4. Turn 2
Step "4" "Voice intake turn 2: must-haves, avoids"
$t2 = Call-Api "POST" "/voice_intake/turn" @{
    session_id = $sid
    user_text  = "I need a large corner sofa, wooden coffee table, and warm ambient lighting. Avoid dark, industrial, or leather."
}
$snip2 = $t2.assistant_text.Substring(0, [Math]::Min(120, $t2.assistant_text.Length))
Info "AI: $snip2..."
Info "must_haves : $($t2.brief.must_haves -join ', ')"
Info "avoid      : $($t2.brief.avoid -join ', ')"
Info "missing    : $($t2.missing_fields -join ', ')"
Info "done       : $($t2.done)"
if (-not $t2.brief.must_haves) { Fail "must_haves not extracted" }

# 5. Session state
Step "5" "Session state before finalize"
$pre = Call-Api "GET" "/session/$sid"
Info "status : $($pre.status)"
Info "brief  : $($pre.brief | ConvertTo-Json -Compress)"

# 6. Finalize
Step "6" "Finalize: generating Miro board (2-4 min)"
$t0 = Get-Date
Info "Started at $(Get-Date -Format 'HH:mm:ss')..."
$fin = Call-Api "POST" "/voice_intake/finalize" @{ session_id = $sid }
$elapsed = [Math]::Round(((Get-Date) - $t0).TotalSeconds)
if (-not $fin.miro_board_url) { Fail "No miro_board_url in response" }
Ok "Done in ${elapsed}s"
Ok "miro_board_url = $($fin.miro_board_url)"

# 7. Verify
Step "7" "Verify session after finalize"
$post = Call-Api "GET" "/session/$sid"
Info "status              : $($post.status)"
Info "miro.board_url      : $($post.miro.board_url)"
Info "layout_plan present : $($null -ne $post.miro.layout_plan)"

if ($post.status -ne "finalized") { Fail "Expected status=finalized, got $($post.status)" }
if (-not $post.miro.board_url)    { Fail "miro.board_url is empty" }
if ($null -eq $post.miro.layout_plan) { Fail "layout_plan is null - Pass 1 failed" }

$lp = $post.miro.layout_plan
Info "board_name     : $($lp.board_name)"
Info "images count   : $($lp.images.Count)"
Info "stickies count : $($lp.stickies.Count)"
if ($lp.images.Count -lt 5)   { Fail "Expected >= 5 images, got $($lp.images.Count)" }
if ($lp.stickies.Count -lt 8) { Fail "Expected 8 stickies, got $($lp.stickies.Count)" }
$summarySnip = $lp.summary.content.Substring(0, [Math]::Min(100, $lp.summary.content.Length))
Info "summary        : $summarySnip..."

Ok "layout_plan has $($lp.images.Count) images and $($lp.stickies.Count) stickies"

Write-Host ""
Write-Host "ALL TESTS PASSED" -ForegroundColor Green
Write-Host "Board: $($fin.miro_board_url)" -ForegroundColor Green
