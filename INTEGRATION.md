# HomeDesigner Voice Intake — Integration Guide

This document explains how the unified voice intake + text fallback system works end-to-end.

## Architecture Overview

```
Consultation UI
  ├─ VoiceAgent (voice mode)
  │  ├─ ElevenLabs SDK (realtime WebSocket)
  │  └─ Tool callbacks → /voice/session_token, /voice_intake/turn, /voice_intake/finalize
  │
  └─ TextIntake (text mode, ?mode=text)
     ├─ Direct fetch calls
     └─ POST /voice_intake/turn, /voice_intake/finalize

                    ↓
            Voice Intake Agent (Backend)
            ├─ Async turn processing
            ├─ Claude conversation (low temp)
            ├─ JSON brief extraction
            └─ Field validation + missing field detection

                    ↓
           Session State (In-Memory or Supabase)
           └─ Canonical DesignBrief + history + Miro metadata

                    ↓
         Helper Functions (workflow/brief.py)
         ├─ get_brief_for_session()
         ├─ get_session_status()
         └─ get_miro_board_url()

                    ↓
         Downstream Pipeline Stages
         ├─ Furniture Search (uses brief.rooms_priority, budget, style)
         ├─ Floorplan Analysis (uses request image + brief context)
         └─ 3D Placement (uses brief.must_haves, constraints)
```

## Quick Start (Test Both Modes in 5 Minutes)

### 1. Start Backend
```bash
cd backend/src
uv run --project ../../ uvicorn main:app --reload --port 8100
```

### 2. Start Frontend Dev Server
```bash
cd frontend/designer-next
pnpm dev   # Runs on localhost:3000
```

### 3. Test Voice Mode (Requires ElevenLabs Setup)
- Navigate to `http://localhost:3000/consultation/test-session-id`
- Click "Start Consultation"
- Speak naturally into microphone
- Agent captures preferences and generates Miro board

### 4. Test Text Mode (No Third-Party Services Required)
- Navigate to `http://localhost:3000/consultation/test-session-id?mode=text`
- Type your preferences into the text box
- See agent responses in real-time
- Click "Finalize & Generate Miro" when done
- Agent generates board and navigates to session page

### 5. Run Full End-to-End Demo
```bash
# Bash/Mac/Linux
bash verify_intake_flow.sh

# Windows PowerShell
# Use demo_intake.py instead (see below)
python backend/src/demo_intake.py
```

## Canonical Data Schema

All intake data flows through the unified `DesignBrief` Pydantic model in `models/schemas.py`:

```python
DesignBrief(BaseModel):
  budget: float | None                      # EUR
  currency: str = "EUR"
  style: list[str]                          # Modern, Minimalist, Bohemian, etc.
  avoid: list[str]                          # Clutter, Bright colors, etc.
  rooms_priority: list[str]                 # Living room, Bedroom, Kitchen
  must_haves: list[str]                     # >= 2 items required
  existing_items: list[str]                 # Current furniture to keep/reuse
  constraints: list[str]                    # Structural, Budget, Pet-friendly
  vibe_words: list[str]                     # calm, energetic, luxurious
  reference_images: list[str]               # URLs or file paths
  notes: str                                # Open-ended comments
```

### Required Fields for Completion
The agent ensures these are non-empty before setting `done=true`:
- `budget` (is not None)
- `rooms_priority` (non-empty list)
- `style` (non-empty list)
- `must_haves` (>= 2 items)

## Endpoint Reference

### Create Session
```bash
POST /session/new
Headers: Content-Type: application/json
Body: {"client_name": "Optional Name"}
Response: {"session_id": "uuid-string"}
```

### Get Session State
```bash
GET /session/{session_id}
Response: {
  "session_id": "uuid-string",
  "status": "collecting|confirmed|finalized",
  "brief": { ... DesignBrief ... },
  "history": [ ... conversation turns ... ],
  "missing_fields": [ "rooms_priority", "must_haves" ]
}
```

### Single Intake Turn (Voice or Text)
```bash
POST /voice_intake/turn
Headers: Content-Type: application/json
Body: {
  "session_id": "uuid-string",
  "user_text": "I love modern design"
}
Response: {
  "assistant_text": "Great! Tell me more about...",
  "brief": { ... updated DesignBrief ... },
  "missing_fields": [ "rooms_priority" ],
  "done": false
}
```

### Finalize & Generate Miro
```bash
POST /voice_intake/finalize
Headers: Content-Type: application/json
Body: {"session_id": "uuid-string"}
Response: {"miro_board_url": "https://miro.com/app/board/..."}
```

### Get KB Status (Debug)
```bash
POST /tool/kb_get
Headers: Content-Type: application/json
Body: {"session_id": "uuid-string"}
Response: {
  "status": "collecting|finalized",
  "brief": { ... DesignBrief ... },
  "missing_fields": [ ... ],
  "miro_board_url": "https://miro.com/app/board/..." (if finalized)
}
```

## Frontend Integration Points

### Consultation Page (`app/consultation/[id]/page.tsx`)
- **Voice Mode (Default)**: Two-column layout with VoiceAgent component
- **Text Mode (?mode=text)**: Full-width TextIntake component
- Both modes use the same backend endpoints
- On completion, navigates to `/session/{id}` with Miro board

### TextIntake Component Props
```typescript
interface TextIntakeProps {
  sessionId: string;                              // Session ID
  onComplete?: (miroUrl: string) => void;        // Called on finalize
  onBriefUpdate?: (brief: DesignBrief) => void;  // Called on each turn
  onStatusChange?: (status: string) => void;     // Called on status change
}
```

### ElevenLabs Integration
- Realtime SDK initialized in `lib/elevenlabs.ts`
- Tool callbacks handled via HTTP POST to backend endpoints
- Fallback to text mode if agent unavailable

## Environment Variables

Create `.env.local` with:
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8100
NEXT_PUBLIC_ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxxx
```

Backend `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
CLAUDE_MODEL=anthropic/claude-3.5-sonnet
MIRO_API_TOKEN=miro_token_xxxxxxxxxxxxx  (optional)
ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxxx  (optional)
ELEVENLABS_VOICE_ID=voice_xxxxxxxxxxxxx
BACKEND_PUBLIC_URL=http://localhost:8100
```

See `.env.example` for all available options.

## Troubleshooting

### Text mode works, but voice mode doesn't
- Check `NEXT_PUBLIC_ELEVENLABS_AGENT_ID` in frontend `.env.local`
- Check `ELEVENLABS_API_KEY` in backend `.env`
- Agent may need to be published in ElevenLabs dashboard

### Miro board generation returns stub URL
- Check `MIRO_API_TOKEN` is set in backend `.env`
- Stub URL (`https://miro.com/app/demo/...`) is used as fallback
- Real board generation happens on finalize with valid token

### Missing required fields not detected
- Check `voice_intake.py` for `_missing_fields()` logic
- Required: `budget`, `rooms_priority`, `style`, `must_haves` (>= 2)
- Agent won't set `done=true` until all collected

### Session state not persisting between requests
- Current: In-memory dict (fast for hackathon)
- For production: Swap `db.py` session functions to use Supabase
- Same interface, no changes needed elsewhere

## Downstream Integration

Once intake is complete, downstream stages consume the brief via:

```python
from workflow.brief import get_brief_for_session, get_session_status

# In furniture, floorplan, or placement agents:
brief = get_brief_for_session(session_id)
if brief:
    rooms = brief.rooms_priority
    budget = brief.budget
    style = brief.style
    must_haves = brief.must_haves
    # Use brief data to drive search/analysis/placement
```

See `workflow/brief.py` for available helper functions.

## Code Quality Guidelines

- **Logging**: Agent logs key decision points (missing fields detected, brief patch applied, done set)
- **Error Handling**: Claude failures → graceful fallback response, session not found → HTTP 404
- **Type Safety**: All Pydantic models used, no `any` types in type hints
- **Separation of Concerns**: Routes → Agents → Tools → DB layer

## Demo Script

Two equivalent scripts test the full flow:

### Python (Cross-platform)
```bash
cd backend/src
python demo_intake.py
```

### Bash (Mac/Linux)
```bash
bash verify_intake_flow.sh
```

Both perform:
1. Create session
2. Run 6 predefined conversation turns
3. Finalize & generate Miro
4. Display final brief state

Output shows success checkmarks and structured data.

## Next Steps

1. **Furniture Search**: `workflows/furniture_search.py` reads brief and calls browser-use agents
2. **Floorplan Analysis**: `workflows/floorplan.py` reads brief for room context and constraints
3. **3D Spatial Placement**: `workflows/placement.py` uses brief.must_haves and budget for furniture positioning
4. **Checkout**: Brief feeds into Stripe Agent Toolkit for one-click purchase links

Each stage follows the same pattern: pull brief with `get_brief_for_session()`, apply logic, update session state.
