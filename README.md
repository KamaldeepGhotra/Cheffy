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
- **There is no migration tool.** On the hosted database, a new column is a manual `ALTER TABLE` in the Supabase SQL editor, and a new table needs `alter table ... enable row level security` there too.

## Deploy

One shared database, one API, one frontend URL: Supabase project `cheffy` (us-east-2), Render service `cheffy-api` (Ohio, free plan), Vercel project `cheffy` (Andreas's account).

1. **Supabase**: create the project in us-east-2 so it sits next to the API. Open **Connect → Session pooler** and copy that string, host included (user `postgres.<project-ref>`, port 5432; the host cannot be worked out from the region). Not the direct `db.<ref>.supabase.co` string: it is IPv6-only and Render is IPv4-only.
2. **Render**: open https://render.com/deploy?repo=https://github.com/KamaldeepGhotra/Cheffy. `render.yaml` defines `cheffy-api`. Set `DATABASE_URL` (the pooler string), `GEMINI_API_KEY`, and `ALLOWED_ORIGINS` (the Vercel production URL). The API creates its tables on first start; check `https://<service>.onrender.com/health` returns `{"status": "ok"}`.
3. **Lock down Supabase's Data API**: once the tables exist, enable row level security on every table (no policies needed) and turn off **Integrations → Data API → Enable Data API**. The API connects as `postgres`, which bypasses RLS; without this step the tables can be reachable with the project's public anon key.
4. **Vercel**: Vercel will not import a personal repo for a collaborator, so the frontend deploys from the CLI: `cd frontend && vercel --prod`. `VITE_API_URL` (the Render URL) is set as a Production environment variable on the project and baked in at build time, so changing it takes another `vercel --prod`.

After merging to `main`: run `vercel --prod` again for frontend changes, since the Vercel project is not connected to Git. Render redeploys by itself only if Auto-Deploy is on in the service's settings; otherwise use **Manual Deploy → Deploy latest commit**.

On the free plans the API sleeps after 15 idle minutes, so the first request after that takes about a minute, and Supabase pauses the project after 7 days without database activity (restore it from the dashboard).

`ALLOWED_ORIGINS` takes exact origins, so Vercel preview deployments are not supported; only the production URL can call the API.
