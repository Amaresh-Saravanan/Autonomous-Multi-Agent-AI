# Autonomous Multi-Agent AI Platform — Disaster Response

Phase 0 vertical slice: synthetic sensor event → AG-1 (rule-based) →
recommendation with evidence → live map, over a real HTTP + WebSocket API.

Docs: `docs/PRD.md`, `docs/TDD.md`, `docs/UX_DESIGN.md`, `docs/MIGRATION_TRACKER.md`.

## Run it (no Docker needed; Groq API key is optional)

**Without LLM (rule-based fallback):**

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

**With LLM reasoning (Groq free tier):**
Get a free API key at [groq.com](https://console.groq.com/keys), then:
```bash
export GROQ_API_KEY=your_key_here
python -m uvicorn app.main:app --reload
```
AG-1 will use Groq's Mixtral-8x7B for multimodal reasoning; AG-8 will synthesize summaries. Falls back to rule-based if the key is missing or API is unreachable.

Then start the frontend (Next.js + TypeScript + Tailwind, in `frontend-next/`):

```bash
cd frontend-next
npm install
npm run dev      # serves on http://localhost:3000
```

Open [http://localhost:3000](http://localhost:3000), log in with a seed user
(see `docs/RUNBOOK.md`), and you get the live command-center map + draggable
alert/recommendation panels, with a button to simulate a critical sensor
spike. It connects to `localhost:8000`.

## Test it

```bash
cd backend
python -m pytest tests/test_slice.py -v
```

## What's real vs. deferred

### Phase 0/1 (now shipping)
- **Ingestion:** IoT, weather, satellite normalizers (ready for more sources)
- **AG-1 Disaster Assessment:** Groq/Mixtral-8x7B reasoning (multimodal) with
  threshold fallback if LLM unavailable
- **AG-8 Situational Intelligence:** reads full blackboard, synthesizes rolling
  summary via LLM or rule-based join
- **Real-time:** WebSocket push of recommendations to map
- **Frontend:** Next.js + TypeScript + Tailwind app (`frontend-next/`) —
  command-center map, draggable panels, framer-motion, theming, per-role
  layouts, per `docs/UX_DESIGN.md` (the original Phase 0 `frontend/index.html`
  shell has been retired)

### Deferred to Phase 2+ (see `docs/MIGRATION_TRACKER.md`)
- AG-2 (Damage), AG-3 (Rescue), AG-4 (Medical), AG-5 (Resources), AG-6 (Routes),
  AG-7 (Citizen chat)
- Severity grid (H3 hashing)
- Incident clustering
- Postgres/PostGIS + Redis streaming
