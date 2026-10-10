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
uv sync
cp .env.example .env
```
Edit `backend/.env` and set:
- `SUPABASE_URL`: existing NexusCare Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY`: the project's publishable key, used by the backend Supabase client for Auth verification
- `DATABASE_URL`: a Postgres connection string in SQLAlchemy format, for example `postgresql+psycopg://postgres:<PASSWORD>@<HOST>:5432/postgres`

Use the connection type recommended by Supabase for your network. Do not commit `.env`, database passwords, or secret keys.

Run the API:
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Health: http://127.0.0.1:8000/api/v1/health
- API docs: http://127.0.0.1:8000/docs

## Phase 2 database migration
**Review the migration and verify the target project before running this against Supabase.** The migration creates tables and enables row-level security. Do not run it against production data without a backup and review.

From `backend/`, with `DATABASE_URL` configured:
```bash
uv run alembic upgrade head
```

To check the migration version:
```bash
uv run alembic current
```

To seed fictional development data after the migration:
```bash
uv run python scripts/seed_demo.py
```
The seed creates role and reference records plus 20 fictional patients. It does not create Supabase Auth accounts or passwords. Do not use real patient information.

## Authentication and authorization foundation
- Supabase Auth verifies the bearer access token.
- `GET /api/v1/auth/me` returns the signed-in identity and assigned NexusCare role codes.
- `GET /api/v1/admin/access-check` requires the `administrator` role.
- The role must be assigned to the matching profile in `profiles` and `user_roles`; never accept a role supplied by the frontend.
- Sensitive tables use RLS and default-deny policies. FastAPI routes must still enforce role and record-level authorization.
- The Phase 2 role-check endpoint is a foundation, not a complete staff account management interface.

## Phase 2 test checklist
- [ ] `uv sync` completes and dependencies are locked.
- [ ] `uv run pytest` passes.
- [ ] API starts and health endpoint responds.
- [ ] Migration runs on a reviewed development database.
- [ ] RLS is enabled for every application table.
- [ ] Seed command can be run more than once without duplicating seed records.
- [ ] Missing/invalid bearer token is rejected by the auth endpoint.
- [ ] A valid Supabase user without an active profile cannot access role-protected routes.
- [ ] A non-administrator cannot access `/api/v1/admin/access-check`.
- [ ] No credentials or real patient data are committed.

## Known Phase 2 limits
The models and authentication/authorization foundations are in place, but patient CRUD, admissions, clinical, laboratory, pharmacy, billing, and inventory API workflows are future phases. No end-to-end hospital workflow is claimed complete yet.
