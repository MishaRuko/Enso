# HomeDesigner — Quick Demo Launch Guide

**Time to demo**: 5 minutes  
**Requirements**: Node.js, Python 3.10+, OpenRouter API key

---

## 1. Setup (One-Time)

### Install Dependencies
```bash
# From project root
make install
# Or manually:
cd backend && uv venv && source .venv/bin/activate && pip install -r requirements.txt
cd frontend/designer-next && pnpm install
```

### Configure Environment
```bash
# Copy and fill in .env files
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

cp frontend/designer-next/.env.example frontend/designer-next/.env.local
# Frontend can work without keys (text mode fallback)
```

---

## 2. Start Services (New Terminals)

### Terminal 1: Backend (Port 8100)
```bash
cd backend/src
uv run --project ../../ uvicorn main:app --reload --port 8100
```
✓ Wait for: `Uvicorn running on http://127.0.0.1:8100`

### Terminal 2: Frontend (Port 3000)
```bash
cd frontend/designer-next
pnpm dev
```
✓ Wait for: `ready - started server on 0.0.0.0:3000`

---

## 3. Run Demo (Choose One)

### Option A: Text Mode (Recommended for Quick Demo)
**URL**: `http://localhost:3000/consultation/demo-session-1?mode=text`

**Demo Flow**:
1. Page loads with text intake component
2. Type: "I'm redesigning my living room"
3. Type: "I love modern minimalist designs"
4. Type: "My budget is 5000 EUR"
5. Type: "I want a nice sofa and side tables"
6. Type: "No clutter, neutral colors"
7. Type: "Yes, let's finalize"
8. Click "Finalize & Generate Miro"
9. See success message with Miro board URL

**Total time**: 2-3 minutes

---

### Option B: Voice Mode (Requires Setup)
1. Set `NEXT_PUBLIC_ELEVENLABS_AGENT_ID` in `frontend/.env.local`
2. Ensure backend has `ELEVENLABS_AGENT_ID` + `ELEVENLABS_VOICE_ID` + `ELEVENLABS_API_KEY` in `.env`
3. Navigate to: `http://localhost:3000/consultation/demo-session-1` (no ?mode=text)
4. Click "Start Consultation"
5. Speak naturally about your room preferences
6. Agent captures preferences → prompts for completion
7. Say "Yes" or "That's correct"
8. Miro board generated automatically

**Total time**: 3-5 minutes

---

### Option C: Automated End-to-End (CI/Demo Box)

#### Python Script (All Platforms)
```bash
python backend/src/demo_intake.py
```

#### Bash Script (Mac/Linux)
```bash
bash verify_intake_flow.sh
```

Both scripts:
- Create session
- Run 6 predefined conversation turns
- Finalize & generate Miro
- Display final brief state

**Output**: JSON-formatted session with all collected preferences  
**Total time**: 10-15 seconds

---

## 4. What to Show Judges

### Talking Points
1. **Canonical Brief Schema**: "All intake data converts to canonical 11-field JSON"
2. **Flexible Frontend**: "Voice OR text - same backend endpoints"
3. **Claude Validation**: "Agent ensures required fields are collected before completion"
4. **One-Shot Miro**: "Brief automatically generates board layout on finalize"
5. **Clean Handoff**: "Downstream stages (furniture search, placement) consume brief JSON"
6. **Graceful Fallbacks**: "Works without ElevenLabs, Miro, or any third-party token"

### Demo Walkthrough (3 minutes)
1. **Show Setup**: Open 2 terminals, start backend + frontend
2. **Navigate to Demo**: Open `http://localhost:3000/consultation/demo-session-1?mode=text`
3. **Type Natural Input**: "I want a cozy bedroom with warm colors"
4. **Show Agent Response**: Agent extracts data, asks follow-ups
5. **Complete Required Fields**: Type 4-5 messages to collect all fields
6. **Finalize**: Click "Finalize & Generate Miro"
7. **Show Result**: Display Miro board URL + final brief JSON

### Show in Code (1 minute)
- **Canonical Schema**: [models/schemas.py](models/schemas.py#L1-L50) — `DesignBrief` model
- **Agent Logic**: [agents/voice_intake.py](backend/src/agents/voice_intake.py#L150-L230) — `run_voice_intake_turn()`
- **Pipeline Handoff**: [workflow/brief.py](backend/src/workflow/brief.py) — `get_brief_for_session()`

---

## 5. Troubleshooting

### Backend won't start
```bash
# Check port 8100 is free
lsof -i :8100  # Mac/Linux
netstat -ano | findstr :8100  # Windows

# Or use different port
uvicorn main:app --port 8101
```

### Frontend won't start
```bash
# Clear cache and reinstall
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Claude API call fails
```bash
# Check OPENROUTER_API_KEY in backend/.env
echo $OPENROUTER_API_KEY

# Regenerate key at https://openrouter.ai/keys
```

### Text intake gets stuck on "Finalize"
```bash
# Check browser console for errors
# Verify backend is running: curl http://localhost:8100/health
# Check response is 200 OK with status object
```

---

## 6. File Organization for Demo

Keep these visible/bookmarked:
- `INTEGRATION.md` — Architecture + endpoint reference
- `COMPLETION_SUMMARY.md` — Phase 2 overview
- `backend/src/models/schemas.py` — Brief schema
- `backend/src/agents/voice_intake.py` — Agent logic
- `frontend/.../consultation/[id]/page.tsx` — UI conditional rendering

---

## 7. Performance Tips

### Faster Iteration
```bash
# Backend auto-reloads with --reload flag
# Frontend hot-reloads by default

# To clear frontend cache:
Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
```

### Faster Completion
- Use text mode (faster than typing real voice inputs)
- Pre-copy demo conversation from [INTEGRATION.md](INTEGRATION.md#demo-script)
- Use demo script if judges want to see backend JSON directly

---

## 8. Next Demo Stages (Optional)

### After Intake: Furniture Search
1. Click "Browse Furniture" on session page
2. System searches IKEA, Wayfair, Zara for items matching brief
3. Shows 3D previews + price tags

### After Search: 3D Room Placement
1. Click "Arrange Room"
2. Drag furniture into 3D room layout
3. See Miro board update in real-time

### After Placement: One-Click Checkout
1. Click "Buy Now"
2. Stripe payment link pre-populated with selected items
3. Show Stripe invoice preview

---

## Success Checklist

- [ ] Backend running on port 8100
- [ ] Frontend running on port 3000
- [ ] Text intake page loads without errors
- [ ] Agent responds to first message within 3 seconds
- [ ] All 4 required fields collected in <5 messages
- [ ] "Finalize" button triggers Miro generation
- [ ] Miro URL displayed in success message
- [ ] Final brief JSON validates schema

---

## Questions to Prepare For

**Q: "Why both voice and text?"**  
A: Voice is premium UX (hands-free), text is accessible + instant demo (no audio setup).

**Q: "What happens if Claude fails?"**  
A: Graceful fallback response. User can retry. Session state preserved.

**Q: "How do you ensure required fields?"**  
A: Agent validates on each turn. Won't set done=true unless budget, style, rooms, and 2+ must_haves collected.

**Q: "What's next after intake?"**  
A: Furniture search (parallel browser agents), floorplan analysis (Gemini Vision), 3D placement (spatial reasoning).

**Q: "How does this scale?"**  
A: Session-based architecture. Swap in-memory dict for Supabase. Async agents scale horizontally.

---

## Contact & Support

- **Backend Issues**: Check `backend/src/main.py` logs
- **Frontend Issues**: Check browser console (F12)
- **API Issues**: Test with `curl` commands in [INTEGRATION.md](INTEGRATION.md#endpoint-reference)

---

**Ready to demo!** 🎨✨

Start with Terminal 1 + 2, navigate to text-mode URL, and type your way through a room redesign.
