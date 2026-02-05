# drishti
AI-Driven Sustainability Operating System for Urban Water Systems

## Quickstart (Local)

1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Seed a few sensors and create the DB:

```bash
python -m scripts.init_db
```

3. Start the FastAPI backend:

```bash
uvicorn backend.main:app --reload
```

4. (Optional) Run the data generator to simulate sensor readings:

```bash
python scripts/generate_data.py --url http://localhost:8000 --sensors 5 --count 200 --delay 0.3
```

5. Start the Streamlit frontend:

```bash
streamlit run frontend/app.py
```

6. Visit http://localhost:8501 for the dashboard. The backend runs on http://localhost:8000.

---

This repository is a hackathon-friendly prototype. It uses a lightweight SQLite DB by default but can be pointed to a Supabase/Postgres instance by setting the `DATABASE_URL` environment variable.

## Supabase Auth & DB (recommended for deployment) ✅

- Create a free Supabase project at https://app.supabase.com and note the **Project URL** and **anon/public key** (Project -> Settings -> API).
- Enable Email auth in Supabase (Auth -> Settings).
- Set environment variables locally or in deployment:
  - `DATABASE_URL` (Postgres connection string from Supabase)
  - `SUPABASE_URL` (your project URL, e.g. https://xyz.supabase.co)
  - `SUPABASE_KEY` (anon/public key for client-side auth calls)
  - (Optional) `SUPABASE_SERVICE_ROLE_KEY` for any server-side admin tasks — keep secret.

### Applying the DB schema

A SQL migration is included at `migrations/initial.sql` and a small runner `scripts/apply_migrations.py` uses your `DATABASE_URL` to apply it.

Example (local):

```bash
set DATABASE_URL=postgresql://user:pass@host:5432/dbname   # Windows (PowerShell: $env:DATABASE_URL=...)
python scripts/apply_migrations.py
```

If you prefer the Supabase UI, you can paste `migrations/initial.sql` into the SQL editor and run it there.

### Frontend & backend env vars

- Frontend (Streamlit Cloud): set `API_BASE`, `SUPABASE_URL`, `SUPABASE_KEY`.
- Backend (Railway/Render): set `DATABASE_URL` and optionally `SUPABASE_SERVICE_ROLE_KEY`.

### Security notes

- Do not commit service-role keys to source control.
- Use Supabase anon key only in client; use service role key or DB connection string only for the server.


## Tests

Run quick smoke tests locally (no server needed):

```bash
python -m scripts.test_api
python -m scripts.test_ml
```

These use FastAPI's TestClient and simple synthetic data to verify core endpoints and ML functions.

## Dashboard (Streamlit)

The Streamlit app shows an interactive sensor map and details:
- Hover sensors on the map to view latest readings, `last_service`, and unresolved alert count.
- Select a sensor to see metrics and time-series charts.
- Use "Refresh sensor data" in the sidebar to clear the cache and refetch from Supabase.

To run locally:

```bash
streamlit run frontend/app.py
```

When deployed to Streamlit Cloud, set `SUPABASE_URL` and `SUPABASE_KEY` in the app Secrets.

## Deploy (short)

- Backend: Railway or Render — point `start` to `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` and set `DATABASE_URL` as secret.
- Frontend: Streamlit Cloud — push repo, set `API_BASE` to your backend and `SUPABASE_*` env vars in the UI.

---

# Streamlit Cloud Deployment

1. Push the repo to GitHub.
2. On streamlit.io/cloud, create a new app from this repo.
3. In the app settings > Secrets, add:
   - SUPABASE_URL
   - SUPABASE_KEY
4. Deploy. Use the sidebar to enter a table name and view/insert rows.

---

# Quick local setup

## Unix

1. ./setup_venv.sh
2. source .venv/bin/activate
3. streamlit run streamlit_app.py

## Windows

1. setup_venv.bat
2. .venv\Scripts\activate
3. streamlit run streamlit_app.py

Before deploying to Streamlit Cloud, add SUPABASE_URL and SUPABASE_KEY in the app Secrets.
