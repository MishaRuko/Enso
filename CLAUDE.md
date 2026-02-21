# HomeDesigner — AI Interior Design Agent

Voice consultation, furniture search, 3D placement, one-click purchase.

## Structure
```
homedesigner/
├── backend/src/          # FastAPI + multi-agent pipeline
│   ├── agents/           # pipeline agents (planner, scraper, placer)
│   ├── models/           # Pydantic models
│   ├── prompts/          # LLM prompt templates
│   ├── tools/            # agent tool wrappers
│   ├── workflow/         # pipeline orchestration
│   ├── config.py         # env vars + settings
│   └── main.py           # FastAPI app (port 8100)
├── frontend/designer-next/ # Next.js 15 + React Three Fiber
│   └── src/
│       ├── app/          # App Router pages
│       ├── components/   # React components (viewer, chat, sidebar)
│       ├── hooks/        # custom hooks
│       └── lib/          # types, API client, Supabase client
├── supabase/             # local Supabase config + migrations
└── docs/                 # research, strategy, pipeline docs
```

## Dev Commands
- `make install` — install all deps (uv + pnpm) + configure git hooks
- `make dev` / `tilt up` — start backend + frontend via Tilt
- `make dev-down` — stop all
- `make lint` — auto-fix all (biome + ruff)
- `make format` — format only
- `make check` — lint without autofix (CI-style)
- `make build` — Next.js production build

## Linting & Formatting
- **Ruff** for Python (config in `pyproject.toml` `[tool.ruff]`)
- **Biome** for TypeScript (config in `frontend/designer-next/biome.json`)
- **Before every commit**: `make lint` runs automatically via git hook
- Ruff suppression: `# noqa: E501` inline
- Biome suppression: `// biome-ignore lint/rule: reason`

## Code Quality
- Python: type hints, snake_case, line length 100
- TypeScript: strict mode, no `any` types
- No comments unless logic isn't self-evident
- NEVER edit `.env` files

## Documentation
- Plans always in `docs/plans/` (gitignored)
- ALWAYS update CLAUDE.md when introducing new patterns

## Backend
- Entry point: `backend/src/main.py` (FastAPI)
- Run: `cd backend/src && uv run --project ../../ uvicorn main:app --reload --port 8100`
- Imports are relative to `backend/src/` (not package-style)
- All LLM calls via OpenRouter (`openai` SDK with custom base_url)
- Claude Sonnet 4.5 for planning/reasoning
- Gemini 2.5 Pro for vision/spatial reasoning
- 3D generation via fal.ai (TRELLIS 2 primary, Hunyuan3D v2 fallback)

## Frontend — Next.js
- Next.js 15 App Router + React 19 + TypeScript strict
- React Three Fiber for 3D room viewer (client component)
- Supabase for durable session/job persistence
- Polling-based pipeline status
- Biome for lint/format, ESLint `eslint-config-next`
- Run: `cd frontend/designer-next && pnpm dev`
- Proxies `/api/*` to backend:8100 via next.config.ts

### Next.js Code Conventions
- `"use client"` only where needed (event handlers, useState, Three.js)
- Import alias: `@/*` → `src/*`
- CSS variables only — never raw color classes, never `dark:` prefix
- No `any` types — all API shapes typed in `lib/types.ts`
- Server components where possible
- Supabase client in `lib/supabase.ts`; all backend REST in `lib/backend.ts`

### Supabase Tables
- `design_sessions` — one per consultation, stores preferences + floorplan + placements
- `design_jobs` — one per pipeline run, trace + result
- `furniture_items` — cached scraped furniture data per session
- `models_3d` — generated/sourced GLB models

## Pipeline Phases
1. **Booking** — Cal.com widget → schedule consultation
2. **Voice consultation** — ElevenLabs agent interviews user, builds mood board
3. **Floorplan processing** — Nano Banana text removal → Gemini room analysis → procedural 3D room
4. **Furniture search** — Claude shopping list → parallel browser-use agents (IKEA, Wayfair, Zara Home)
5. **3D model generation** — IKEA GLB > Sketchfab > Poly Pizza > fal.ai TRELLIS 2
6. **Spatial placement** — Gemini coordinates + validation
7. **Rendering** — React Three Fiber scene with placed furniture
8. **Purchase** — Stripe Agent Toolkit payment link

## API Design
- `POST /api/sessions` — create design session
- `GET /api/sessions/{id}` — get session state
- `POST /api/sessions/{id}/floorplan` — upload + process floorplan
- `POST /api/sessions/{id}/search` — start furniture search
- `POST /api/sessions/{id}/place` — run spatial placement
- `POST /api/sessions/{id}/checkout` — create Stripe payment link
- `GET /health` — health check
