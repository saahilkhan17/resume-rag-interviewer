# Resume RAG Interviewer

A RAG-based resume interview system built for the PGAGI AI Backend Engineering
Intern assignment (JM-1117-01). Upload a resume, pick a role, and get a
grounded, contextual interview: questions are generated from a knowledge base
retrieved against the candidate's own resume — never from generic templates —
and the session ends with a structured summary.

> **Deadline assumption:** the assignment was received Tue 2026-11-17
> afternoon IST with a 48h window, so this build targets ~Thu 2026-11-19
> ~15:00 IST.

## How it works

```
Resume (PDF/text) + role
  → resume parsing (skills, technologies, domains)
  → dynamic queries from resume + role
  → RAG: KB ingestion → chunking → TF-IDF index → role-scoped retrieval
  → grounded question generation (Gemini if a key is set, else extractive fallback)
  → interactive interview (session continuity, stored answers)
  → structured summary (strengths, gaps, per-question assessment)
```

## Quick start

```bash
cd resume-rag-interviewer
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
# Optional: copy backend/.env.example to backend/.env and set GEMINI_API_KEY
# (without a key the system works fully via the grounded fallback generator)
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
# or: ./scripts/verify.sh   (venv + tests + boot + full API smoke flow)
```

Then open http://localhost:8000/docs for the interactive API, or run the
React frontend (see `frontend/`).

## API contract

Base `/api`. Errors are `{detail: ...}` with proper HTTP codes.

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` |
| GET | `/api/roles` | `[{id, label, description, kb_chunks}]` |
| POST | `/api/sessions` | multipart `resume` file (.pdf/.txt/.md) + `role` form field → **201** `{session_id, role, parsed_profile, status:"created"}`. Missing file → 422; unsupported type → 415; unknown role → 422 |
| GET | `/api/sessions/{id}` | session state incl. parsed profile, status, question/answer counts |
| POST | `/api/sessions/{id}/start` | builds context, retrieves chunks, generates questions → `{status:"in_progress", questions:[{id, text, topic, difficulty, source_chunks, trace:{query, chunk_ids}}]}` (default 5). No grounded content → 503 |
| GET | `/api/sessions/{id}/questions` | questions with traceability |
| POST | `/api/sessions/{id}/answers` | `{question_id, answer_text}` → **201** `{answer_id, question_id, stored_at}`. Empty answer → 422; unknown question → 404 |
| POST | `/api/sessions/{id}/complete` | structured summary (see below) |
| GET | `/api/sessions/{id}/summary` | stored summary; 404 if not completed |
| GET | `/api/sessions` | list sessions |
| DELETE | `/api/sessions/{id}` | deletes session + Q&A → 200 |

Summary shape:

```json
{
  "status": "completed",
  "summary": {
    "overall_assessment": "...",
    "strengths": ["..."],
    "gaps": ["..."],
    "per_question": [
      {"question_id": "...", "question": "...", "answer": "...",
       "assessment": "...", "key_points_covered": ["..."],
       "key_points_missed": ["..."]}
    ],
    "topics_covered": ["..."],
    "recommended_next_steps": ["..."]
  }
}
```

Roles: `ai-ml-engineer` (AI/ML Engineer), `data-science`
(Data Science / Applied ML), `backend-engineer` (Backend Engineer).

## Architecture

```
backend/
  app/
    main.py            # FastAPI factory, CORS, routers, startup warm-up
    config.py          # pydantic-settings (GEMINI_API_KEY optional, DATABASE_URL, KB_DIR, EMBEDDING_PROVIDER)
    database.py        # SQLAlchemy engine/session, SQLite
    models.py          # Session, Question, Answer, Summary tables
    schemas.py         # Pydantic request/response models
    api/
      sessions.py      # session endpoints
      roles.py         # GET /api/roles
    services/
      resume_parser.py   # PDF/text extraction; skill/tech/domain lexicon
      context_builder.py # dynamic queries + topic selection from resume + role
      interview.py       # session lifecycle, answer storage, completion
      summarizer.py      # structured summary from Q&A + traces
    rag/
      chunker.py           # section-aware recursive chunking (~600 chars, 120 overlap, keeps headings)
      embeddings.py        # TF-IDF vectorizer (default) + optional Gemini embeddings
      vector_store.py      # persisted TF-IDF index (backend/data/vector_store/)
      ingestion.py         # load .md/.txt/.pdf from KB_DIR; CLI: python -m app.rag.ingestion --rebuild
      retriever.py         # dynamic query → top-k chunks with scores, role-scoped
      question_generator.py# Gemini adapter + grounded extractive fallback
  data/kb/*.md         # seed KB (own-word concept notes, role-tagged)
  tests/               # pytest suite (≥30 tests)
  requirements.txt
  .env.example
scripts/
  verify.sh            # venv install + pytest + boot + full API smoke flow
  demo_record.py       # Playwright script recording demo/demo.mp4 of the real UI
frontend/              # React (Vite) — upload → role select → interview → results
```

## Design decisions

- **TF-IDF retrieval by default:** zero-cost, zero-key, deterministic and
  explainable. Gemini embeddings / LLM question generation are optional
  upgrades behind env vars. The assignment's RAG reasoning (chunking,
  retrieval quality, grounding) is demonstrated either way.
- **SQLite, not Postgres:** one-command demo, no Docker needed. SQLAlchemy
  models make a Postgres swap trivial (change `DATABASE_URL`).
- **Grounded fallback question generator:** questions are composed from
  retrieved chunk propositions + the candidate's own skills, chosen per
  chunk by token overlap, so they are contextual by construction. When no
  relevant chunk exists the system answers 503 instead of inventing a
  generic question.
- **Traceability:** every question stores its retrieval query + source chunk
  ids; the UI shows topic + source concepts per question.

## Knowledge base — honest note

The seed KB (`backend/data/kb/*.md`, 13 own-word concept notes with YAML
frontmatter `roles:` / `topics:`) is the shipped knowledge base. The
assignment named the Mitchell / Burkov / Brownlee textbooks, but those PDFs
were **not supplied as files** (only "Download PDF" placeholders), and they
are copyrighted, so **no textbook PDFs are bundled**. The loader also
ingests PDFs dropped into `backend/data/kb/` — drop a book PDF there and
run `python -m app.rag.ingestion --rebuild` (from `backend/`) to extend the
KB. The seed notes cover gradient descent, neural networks, supervised /
unsupervised learning, evaluation metrics, overfitting, RAG, NLP
embeddings, REST APIs / FastAPI, databases, auth/JWT and async queues.

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` | (empty) | Optional. When set, Gemini generates questions (model `gemini-1.5-flash`) and embeddings are available; without it the grounded fallback runs everything. No key is available in this environment, so the LLM path is implemented + tested with a stub and is live only if a key is provided. |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite file under `backend/data/` |
| `KB_DIR` | `data/kb` | Relative to `backend/` |
| `EMBEDDING_PROVIDER` | `tfidf` | `tfidf` (default) or `gemini` |
| `NUM_QUESTIONS` | `5` | Questions per interview |

## Tests & verification

```bash
cd backend && ../.venv/bin/python -m pytest tests/ -q   # ≥30 tests
./scripts/verify.sh   # full gate: venv install, pytest, boot server,
                      # GET /health, full API smoke flow (create → start →
                      # answer all → complete → summary); exits non-zero on failure
```

## Demo

```bash
pip install playwright && playwright install chromium   # once, for the demo script
python scripts/demo_record.py   # Playwright; needs the backend on :8000 and
                                # the frontend dev server on :5173; writes demo/demo.mp4
```

## Honest limits

- No Gemini key in this environment: LLM generation is implemented and
  unit-tested with a stub, live only with `GEMINI_API_KEY`.
- No textbook PDFs bundled (not supplied; copyrighted) — see KB note above.
- The demo video is recorded from the real running UI via Playwright; if
  the recording pipeline fails, that is reported, never faked.
