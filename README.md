# Cheffy

Meal prep for two roommates: a shared inventory of what is in the kitchen, recipes ranked by what is on hand, a weekly meal plan, and a grocery list that is the recipes you picked minus what you already have.

Backend: FastAPI + SQLAlchemy in `backend/`. Frontend: React + Vite in `frontend/`. The plan and contracts both of us build against live in `docs/superpowers/plans/2026-09-11-mvp-plan.md`.

## Run it locally

Backend (Python 3.12; `rapidfuzz` does not build on newer interpreters):

```bash
cd backend
uv venv --python 3.12 && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put your Gemini key in it
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend talks to http://localhost:8000 unless `VITE_API_URL` says otherwise.

Tests: `cd backend && python -m pytest` and `cd frontend && npm test`.

## Things that bite

- **Delete `backend/cheffy.db` after any schema change.** Tables are created with `create_all`, which never alters an existing table. A stale file shows up as `OperationalError` about a missing column.
- **`uvicorn --reload` has been unreliable here.** If a backend change does not seem to take effect, stop the server fully and start it again before debugging anything else.
- **There is no migration tool.** On the hosted database, a new column is a manual `ALTER TABLE` in the Supabase SQL editor.

## Deploy

One shared database, one API, one frontend URL. Do this after every schema change in the plan has landed on `main`.

1. **Supabase**: create a project, open Settings → Database, copy the connection string. Tables are created by the API on first start.
2. **Render**: create a Blueprint from this repo; `render.yaml` defines the `cheffy-api` web service. Set `DATABASE_URL` (the Supabase string), `GEMINI_API_KEY`, and `ALLOWED_ORIGINS` (the Vercel production URL) in the service's environment. Check `https://<service>.onrender.com/health` returns `{"status": "ok"}`.
3. **Vercel**: import the repo with `frontend` as the root directory (Vite preset) and set `VITE_API_URL` to the Render URL.

`ALLOWED_ORIGINS` takes exact origins, so Vercel preview deployments are not supported; only the production URL can call the API.
