# HomeDesigner AI — Demo Script (3 minutes)

## Elevator Pitch (30 seconds)

"Imagine redesigning your room just by talking. HomeDesigner is an AI interior design assistant that listens to your style preferences through voice, searches real IKEA furniture within your budget, places everything in a 3D room you can walk through, and lets you buy it all in one click. From conversation to checkout in under 5 minutes."

---

## Demo Flow (2 minutes 30 seconds)

### Step 1 — Voice Consultation (40s)
1. Open `http://localhost:3000`
2. Click **"Start New Design"**
3. The ElevenLabs voice agent greets you: "Hi! I'm your AI interior designer."
4. Speak: "I want a modern minimalist living room, budget around 3000 euros, light colours"
5. The agent asks follow-up questions about lifestyle, must-haves
6. Preferences appear in the sidebar in real-time

**Key point:** Natural voice conversation powered by ElevenLabs Conversational AI + Claude Sonnet for understanding.

### Step 2 — Room Setup (20s)
1. Upload a floorplan image (or use the built-in room dimension editor)
2. Gemini 2.5 Pro analyzes the floorplan image, extracts walls/doors/windows
3. Room appears as a 3D wireframe in the viewer

**Key point:** Gemini vision understands architectural drawings and extracts structured room data.

### Step 3 — Furniture Search (30s)
1. Click **"Find Furniture"** (or it auto-triggers from the pipeline)
2. Claude generates a shopping list from your preferences
3. browser-use scrapes real IKEA products with prices, images, dimensions
4. Results appear as a shoppable grid — toggle items on/off
5. Show the Miro mood board link for visual inspiration

**Key point:** Real products, real prices from IKEA. Not stock photos.

### Step 4 — 3D Room Visualization (30s)
1. Click **"Place Furniture"**
2. Gemini spatially reasons about where each item goes (avoids doors, faces windows)
3. The 3D room renders with furniture placed — orbit, zoom, walk through
4. Drag to reposition if desired

**Key point:** Spatial AI placement validated against room constraints. Three.js + React Three Fiber rendering.

### Step 5 — Checkout (30s)
1. Click **"Buy This Room"**
2. Stripe checkout shows the total with all selected items
3. Complete payment (use test card `4242 4242 4242 4242`)
4. Confirmation screen with order summary

**Key point:** End-to-end from voice to purchase. Stripe Agent Toolkit handles payment.

---

## Key Talking Points per Sponsor

### Anthropic
- Claude Sonnet 4.5 powers the voice consultation understanding and shopping list generation
- Structured output with Pydantic schemas for reliable JSON
- Multi-turn conversation via ElevenLabs + Claude backend

### Google (Gemini)
- Gemini 2.5 Pro for floorplan image analysis (vision)
- Gemini 2.5 Pro for spatial reasoning in furniture placement
- Iterative validation loop: Gemini proposes placement, validator checks constraints, Gemini retries

### Stripe
- Stripe Agent Toolkit for checkout flow
- Real payment links generated from furniture selections
- Per-item line items with IKEA product names and prices

### ElevenLabs
- Conversational AI agent for the voice consultation
- Natural multi-turn dialogue — asks follow-ups, confirms preferences
- Real-time transcript displayed in the UI

### Miro
- Mood board generation from design preferences
- Visual collage of style references + selected furniture images
- Shareable link for client collaboration

### Paid (Agentic AI Track)
- Full agentic pipeline: voice input -> LLM reasoning -> web scraping -> 3D generation -> spatial placement -> payment
- Multi-model orchestration: Claude for language, Gemini for vision/spatial, browser-use for web
- Autonomous decision-making at each pipeline stage with fallback handling

### BearingPoint
- Real-world business use case: interior design consultation automation
- End-to-end customer journey from discovery to purchase
- Measurable business value: reduces design consultation time from hours to minutes

---

## Fallback Plan

If live APIs fail during the demo, the system has built-in fallbacks:

### Pre-seeded Demo Data
- Hit `POST /api/demo/seed` before the demo to create 3 fully populated sessions
- Living Room, Bedroom, and Home Office — all with real IKEA data and valid placements
- Navigate to any pre-seeded session to show the full 3D experience

### API Failure Recovery
| Component | Failure | Fallback |
|-----------|---------|----------|
| ElevenLabs voice | Agent doesn't connect | Type preferences manually in the sidebar form |
| Claude (shopping list) | API timeout / error | Pipeline auto-loads demo furniture for the room type |
| IKEA scraper | Website blocks / timeout | Pipeline auto-loads demo furniture for the room type |
| Gemini (placement) | API timeout / error | Pipeline auto-loads demo placement coordinates |
| Stripe checkout | API error | Show the "payment link generated" step, explain Stripe integration |
| Miro board | API error | Show screenshot of a pre-generated mood board |
| 3D rendering | Browser WebGL issue | Switch to Chrome, clear GPU cache, or use pre-recorded video |

### Emergency Demo (no APIs needed)
1. Seed all demos: `curl -X POST http://localhost:8100/api/demo/seed`
2. Open `http://localhost:3000/session/{session_id}` with a returned session ID
3. The 3D room, furniture list, and placement are all pre-loaded
4. Walk through the UI explaining each feature
5. Show the code and architecture for the agentic pipeline

### Pre-demo Checklist
- [ ] Run `curl http://localhost:8100/health` — backend is up
- [ ] Run `curl http://localhost:3000` — frontend is up
- [ ] Seed demo data: `curl -X POST http://localhost:8100/api/demo/seed`
- [ ] Test microphone permissions in browser
- [ ] Have backup browser tab with pre-seeded session open
- [ ] Stripe test mode enabled with test API key
- [ ] Screen recording software ready as final backup
