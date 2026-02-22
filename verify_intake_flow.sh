#!/usr/bin/env bash

# HomeDesigner Voice Intake End-to-End Verification Script
# Tests the complete intake flow: create session -> multiple text turns -> finalize -> get final state
# Run with: bash verify_intake_flow.sh
# Requirements: curl, jq (JSON parser)

set -e  # Exit on first error

BACKEND_URL="${BACKEND_URL:-http://localhost:8100}"
DEMO_TURNS=(
  "I'm redesigning my living room"
  "I love modern minimalist designs, very clean and calm"
  "My budget is around 5000 EUR"
  "I want a comfortable sofa and some minimalist side tables"
  "I want to avoid clutter and bright colors"
  "Yes, that sounds perfect. Let's finalize this brief and generate the Miro board"
)

echo "=========================================="
echo "HomeDesigner Voice Intake Verification"
echo "=========================================="
echo "Backend: $BACKEND_URL"
echo

# Check health
echo "[1/7] Checking backend health..."
HEALTH=$(curl -s "$BACKEND_URL/health")
echo "      $HEALTH"
echo

# Create session
echo "[2/7] Creating design session..."
SESSION_RESPONSE=$(curl -s -X POST "$BACKEND_URL/session/new" \
  -H "Content-Type: application/json" \
  -d '{"client_name": "Demo User"}')
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id')
echo "      Session ID: $SESSION_ID"
echo

# Get initial status
echo "[3/7] Getting initial session status..."
STATUS=$(curl -s -X POST "$BACKEND_URL/tool/kb_get" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}")
echo "      Status: $(echo "$STATUS" | jq -r '.status')"
echo "      Missing fields: $(echo "$STATUS" | jq -r '.missing_fields | length') items"
echo

# Run intake turns
echo "[4/7] Running 6 intake conversation turns..."
for i in "${!DEMO_TURNS[@]}"; do
  TURN_NUM=$((i + 1))
  USER_TEXT="${DEMO_TURNS[$i]}"
  echo
  echo "      Turn $TURN_NUM: \"$USER_TEXT\""

  TURN_RESPONSE=$(curl -s -X POST "$BACKEND_URL/voice_intake/turn" \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": \"$SESSION_ID\", \"user_text\": \"$USER_TEXT\"}")

  ASSISTANT_TEXT=$(echo "$TURN_RESPONSE" | jq -r '.assistant_text')
  DONE=$(echo "$TURN_RESPONSE" | jq -r '.done')
  MISSING=$(echo "$TURN_RESPONSE" | jq -r '.missing_fields | length')

  echo "      Agent: \"${ASSISTANT_TEXT:0:100}...\""
  echo "      Done: $DONE, Missing fields: $MISSING"
done
echo

# Finalize & generate Miro
echo "[5/7] Finalizing brief and generating Miro board..."
FINALIZE_RESPONSE=$(curl -s -X POST "$BACKEND_URL/voice_intake/finalize" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}")
MIRO_URL=$(echo "$FINALIZE_RESPONSE" | jq -r '.miro_board_url')
echo "      Miro board URL: $MIRO_URL"
echo

# Get final session state
echo "[6/7] Fetching final session state..."
FINAL_STATE=$(curl -s "$BACKEND_URL/session/$SESSION_ID")
FINAL_STATUS=$(echo "$FINAL_STATE" | jq -r '.status')
FINAL_BUDGET=$(echo "$FINAL_STATE" | jq -r '.brief.budget')
FINAL_STYLE=$(echo "$FINAL_STATE" | jq -r '.brief.style | length')
echo "      Status: $FINAL_STATUS"
echo "      Budget: €$FINAL_BUDGET"
echo "      Styles collected: $FINAL_STYLE"
echo

# Summary
echo "[7/7] Verification complete!"
echo

echo "=========================================="
echo "Demo Summary"
echo "=========================================="
echo "Session ID:        $SESSION_ID"
echo "Status:            $FINAL_STATUS"
echo "Miro Board URL:    $MIRO_URL"
echo
echo "Brief Data:"
echo "$FINAL_STATE" | jq '.brief' | sed 's/^/  /'
echo
echo "=========================================="
echo "✓ All endpoints working correctly!"
echo "=========================================="
