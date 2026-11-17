# Resume RAG Interviewer — Frontend

React + Vite app for the PGAGI assignment project `resume-rag-interviewer`.
It drives the full interview flow against the FastAPI backend on
`http://localhost:8000` (see `~/workspace/job-agent/pgagi-build/SPEC.md` for the frozen API contract).

## Run

```bash
npm install
npm run dev        # http://localhost:5173 (proxies /api and /health to :8000)
npm run build      # production build -> dist/
npm run preview    # serve the production build
```

The backend must be running on `http://localhost:8000` for any data to load.
If it is not reachable the app shows a "Backend Offline" indicator and an
error banner — it never invents or fakes data.

## Flow (state preserved across stages)

1. **Upload + role** — role cards from `GET /api/roles`; resume file picker
   (`.pdf` / `.txt` / `.md`, client-side extension check); submit creates a
   session and shows the parsed profile as chips
   (skills / technologies / domains / experience hint).
2. **Interview** — `POST /api/sessions/{id}/start` returns 5 questions; one at
   a time with "Question n of 5" progress, topic + difficulty badges, and a
   "Grounded in" line listing the topic and source chunk ids
   (`source_chunks` + `trace.chunk_ids`). Textarea answer, "Save & Next",
   "Back" to revisit earlier questions, answered checkmarks in the progress
   strip. Answers are POSTed to the API as the user advances.
3. **Results** — "Finish & get summary" calls `POST .../complete` and renders
   the overall assessment, strengths, gaps, per-question breakdown (question,
   your answer, assessment, key points covered/missed), topics covered, and
   recommended next steps.
4. **Extras** — dismissible error banners (API `{detail}` messages), loading
   states with disabled buttons, "Start new session" reset, and a "Past
   Sessions" drawer (list / resume / delete via the sessions API).

## Files

- `src/api.js` — fetch client for every endpoint in the contract; throws an
  `Error` carrying the API `detail` string on non-2xx responses.
- `src/App.jsx` — the whole 3-stage flow in one component.
- `src/App.css` — plain CSS, responsive, no frameworks or paid assets.
- `vite.config.js` — dev proxy: `/api` and `/health` → `http://localhost:8000`.
