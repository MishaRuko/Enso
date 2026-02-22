## About the project

Enso is the world's first independent AI interior designer — a multi-agent pipeline that handles the entire journey from consultation to checkout.

It started with a personal problem. Danila's parents work in real estate, and he watched them spend hours staging apartments, coordinating movers, and juggling five different tools just to furnish a single space. After winning the BFL Hack with HouseView (an AI floorplan-to-3D pipeline) and having conversations with industry players like Zillow and Dwelly, the team knew the next step was automating the full interior design workflow end-to-end.

Enso works in four steps:

1. **Describe** — A voice consultation agent powered by ElevenLabs interviews you about your style, budget, and space, building a structured design brief.
2. **Curate** — A curation agent driven by Claude searches real IKEA catalogs in parallel to find furniture that matches your vision, scoring and ranking every match.
3. **Visualize** — A spatial agent uses Gemini to analyze your floorplan, generates a 3D room model via TRELLIS 2, and computes furniture placement coordinates.
4. **Purchase** — The fully furnished 3D scene renders in-browser via React Three Fiber, and Stripe handles one-click checkout for everything.

Five specialized agents, one seamless pipeline — from natural conversation to a furnished 3D room you can buy from.

## Built with

- **Claude Opus 4.6** — planning, reasoning, and furniture curation agent
- **Gemini 3.1 Pro** — floorplan analysis and spatial placement agent
- **ElevenLabs** — voice consultation agent
- **TRELLIS 2 (fal.ai)** — 3D room generation from floorplans
- **Hunyuan3D v2 (fal.ai)** — furniture 3D model generation (fallback)
- **Stripe Agent Toolkit** — one-click payment links
- **React Three Fiber** — interactive 3D room viewer
- **Next.js 15 + React 19** — frontend (App Router, TypeScript strict)
- **FastAPI + Python 3.12** — backend and agent orchestration
- **Supabase** — PostgreSQL database for sessions, jobs, and furniture data
- **OpenRouter** — unified LLM gateway
