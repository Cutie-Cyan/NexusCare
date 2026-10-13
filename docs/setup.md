# Local Setup — NexusCare

**Official title:** Development of an Integrated Hospital Information and Resource Management System

## Prerequisites
- Git
- Bun
- Python 3.11+
- uv
- Access to the existing NexusCare Supabase project and its Postgres connection details

## Clone and switch branch
```bash
git clone https://github.com/Cutie-Cyan/NexusCare.git
cd NexusCare
git fetch origin
git switch develop
```

## Frontend
```bash
cd frontend
bun install
cp .env.example .env
bun run dev
```
Open the URL printed by Vite, normally http://localhost:5173.

## Backend
Open a second terminal from the repository root:
```bash
cd backend
uv lock
uv sync
cp .env.example .env
```

Set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `DATABASE_URL` in `backend/.env`. Use the URL and publishable key from the existing NexusCare project. Use the database URI from Supabase **Connect**, in SQLAlchemy format `postgresql+psycopg://...`; URL-encode special characters in the password if needed. Never commit `.env`.

Run tests and start the API:
```bash
uv run pytest
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Health: http://127.0.0.1:8000/api/v1/health
- API docs: http://127.0.0.1:8000/docs

## Database migration
Review `backend/alembic/versions/20261010_0001_initial_schema.py` and verify the target project before running the migration. This creates the initial tables and RLS policies. Do not run against a production database without backup/review.

From `backend/`:
```bash
uv run alembic upgrade head
uv run alembic current
```

## Fictional demo data
After migration:
```bash
uv run python scripts/seed_demo.py
```
This idempotently seeds role and department reference records, service/lab/medicine catalog items, 20 fictional patients, two wards, and 15 fictional beds. No real patient information should be used.

Optional: create five fictional doctor accounts only if you intentionally want them in the Supabase Auth project. Set server-only `SUPABASE_SECRET_KEY` and a development-only `SEED_DOCTOR_PASSWORD` (at least 12 characters) in `backend/.env`, then run `uv run python scripts/seed_demo.py --create-auth-users`. Never use demo credentials in production.

## Current implementation status
- Phase 1: repository scaffolding and documentation.
- Phase 2: schema/migration foundation, Supabase Auth verification, RBAC dependency, fictional seed script.
- Phase 3: patient registration, search, retrieval, demographic update, soft deactivation.
- Phase 4: ward/bed management, admission, bed transfer, discharge, audit logging.
- Not yet implemented: emergency triage, clinical encounters/consultations, nursing, laboratory, pharmacy, billing, inventory, appointments, notifications UI, and analytics.

**Security note:** direct SQLAlchemy access does not automatically enforce Supabase RLS based on the signed-in user. FastAPI role checks currently protect these routes, but staff access must be tightened to department/encounter-specific scopes before production. Do not use real patient data.
