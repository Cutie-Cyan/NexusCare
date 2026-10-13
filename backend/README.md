# NexusCare Backend

FastAPI REST backend for **Development of an Integrated Hospital Information and Resource Management System**.

## Stack
- Python 3.11+
- FastAPI + Pydantic
- SQLAlchemy 2 + Alembic
- Supabase Auth via `supabase-py`
- Supabase-hosted PostgreSQL
- `uv` for dependencies and execution

## Local setup
From this directory:

```bash
uv lock
uv sync
cp .env.example .env
```

Set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `DATABASE_URL` in `.env`. The database URL must point to the existing NexusCare Supabase Postgres database and use the SQLAlchemy `postgresql+psycopg://` scheme. Never commit `.env`.

Run tests and start the API:

```bash
uv run pytest
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## Implemented endpoints
- `GET /api/v1/health` — process health check
- `GET /api/v1/auth/me` — current Supabase-authenticated identity and assigned roles
- `GET /api/v1/admin/access-check` — administrator-only authorization check
- `GET /api/v1/patients?q=&limit=20&offset=0` — search/list active patient records
- `GET /api/v1/patients/{patient_id}` — read a patient record
- `POST /api/v1/patients` — register a patient (administrator or information officer)
- `PATCH /api/v1/patients/{patient_id}` — update demographics (administrator or information officer)
- `DELETE /api/v1/patients/{patient_id}` — deactivate a record without deleting history (administrator or information officer)
- `GET /api/v1/wards` — list active wards for authorized roles
- `GET /api/v1/beds?ward_id=&available_only=true` — list bed status and availability
- `GET /api/v1/admissions?patient_id=&active_only=true&limit=50&offset=0` — list admissions
- `GET /api/v1/admissions/{admission_id}` — read one admission
- `POST /api/v1/admissions` — admit a patient (administrator or information officer)
- `POST /api/v1/admissions/{admission_id}/discharge` — discharge a patient and release the bed (administrator or information officer)

All patient endpoints require a valid Supabase bearer access token and an active NexusCare profile. Patient accounts can only list/view their own linked patient record. Patient registration and changes are written to `audit_logs`. Medical record numbers are unique and immutable after creation.

## Database migration
The initial migration has not been applied automatically. Review `docs/setup.md` and the migration before running `uv run alembic upgrade head` against the development Supabase project. Do not run migrations against production without a backup and review.

## Phase 4: admissions and bed management
Admission and bed endpoints require a valid Supabase bearer token and an active NexusCare profile. Only administrators and information officers can admit or discharge. Doctors and nurses can view admissions; patient accounts can view only admissions linked to their own patient record. Bed assignment uses database row locks to reduce concurrent double-booking, checks that the bed is available and its ward active, and updates the bed and admission in one transaction. Discharge releases the bed and preserves admission history. Audit events are recorded.

This phase does not yet implement ward transfers, encounter/clinical workflows, department-specific access scopes, or production clinical validation. Staff access must be tightened to assigned care relationships before production use. No real patient data should be used in demo or test environments.
