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

Frontend environment variables are prefixed with `VITE_`. Never put a database password, Supabase secret/service-role key, or signing secret into frontend environment variables.

## Backend
Open a second terminal from the repository root:
```bash
cd backend
uv lock
uv sync
cp .env.example .env
```

Edit `backend/.env` and set:
- `SUPABASE_URL`: existing NexusCare Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY`: the project's publishable key, used by the backend Supabase client for Auth verification
- `DATABASE_URL`: a Postgres connection string in SQLAlchemy format, e.g. `postgresql+psycopg://postgres:<PASSWORD>@<HOST>:5432/postgres`

Use the connection type recommended by Supabase for your network. URL-encode special characters in the password where necessary. Do not commit `.env`, database passwords, or secret keys.

Run the API:
```bash
uv run pytest
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Health: http://127.0.0.1:8000/api/v1/health
- API docs: http://127.0.0.1:8000/docs

## Database migration
**Review the migration and verify the target project before running this against Supabase.** The migration creates tables and enables row-level security. Do not run it against production data without a backup and review.

From `backend/`, with `DATABASE_URL` configured:
```bash
uv run alembic upgrade head
uv run alembic current
```

To seed fictional development data after the migration:
```bash
uv run python scripts/seed_demo.py
```
The default seed creates role and reference records plus 20 fictional patients. Do not use real patient information. To also create five fictional doctor accounts in the existing Supabase Auth project, first set the server-only `SUPABASE_SECRET_KEY` and a development-only `SEED_DOCTOR_PASSWORD` (at least 12 characters) in `backend/.env`, then explicitly run `uv run python scripts/seed_demo.py --create-auth-users`. This modifies Supabase Auth, so only run it when you intentionally want those demo accounts. Never use the demo password in production.

## Phase 3: Patients API
- Run `uv run pytest` before starting the API.
- Start FastAPI and open http://127.0.0.1:8000/docs.
- Authenticate with a valid Supabase access token to try the patient endpoints.
- Registration, demographic updates, and deactivation are limited to the administrator and information officer roles.
- A patient account can only read/list the patient record linked to its own NexusCare profile.
- Deactivation is a soft action (`is_active = false`), not a hard delete.
- Patient changes are logged in `audit_logs`.

Staff access is role-gated for this initial phase, but patient/encounter/department scope must be tightened before production deployment. The direct SQLAlchemy connection is privileged separately from Supabase RLS; FastAPI must enforce authorization for every route.

## Current implementation status
- Phase 1: repository, app scaffolding, documentation.
- Phase 2: schema/migration foundation, Supabase Auth verification, RBAC dependency, fictional seed script.
- Phase 3: patient registration, search, retrieval, demographic update, and soft deactivation endpoints.
- Not yet implemented: admissions, beds, clinical encounters, nursing, labs, pharmacy, billing, inventory, appointments, notifications UI, and analytics workflows.

Generate and commit `backend/uv.lock` in an environment with package registry access. Do not commit `.env` or any secrets.
