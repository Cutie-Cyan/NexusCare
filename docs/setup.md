# Local Setup — NexusCare (Phase 1)

Prerequisites: Git, Bun, Python 3.11+, uv, and access to the existing Supabase project NexusCare.

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

Frontend variables: VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY. These are optional in Phase 1. Never put a service-role/secret key or database password in a VITE_ variable.

## Backend (second terminal)
```bash
cd backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Health: http://127.0.0.1:8000/api/v1/health. API docs: http://127.0.0.1:8000/docs.

Backend variables: APP_ENV, API_V1_PREFIX, CORS_ORIGINS, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, optional server-only SUPABASE_SECRET_KEY, and optional DATABASE_URL for later SQLAlchemy/Alembic tasks. Keep secrets out of Git. No schema or auth integration is created in Phase 1.

## Phase 1 test checklist
- [ ] Frontend starts without compile errors.
- [ ] Desktop sidebar collapses to icons and expands on hover/focus without moving content.
- [ ] Routes and active state work.
- [ ] Mobile drawer opens/closes.
- [ ] Theme toggle works.
- [ ] API health returns JSON.
- [ ] No credentials are committed.

All hospital pages are starter placeholders. Do not enter real patient data.
