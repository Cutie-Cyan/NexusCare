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

Set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `DATABASE_URL` in `.env`. Use the existing NexusCare Supabase project. Never commit `.env`.

Run tests and start the API:

```bash
uv run pytest
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## Implemented endpoints
- `GET /api/v1/health` — API process health check
- `GET /api/v1/auth/me` — current Supabase-authenticated identity and roles
- `GET /api/v1/admin/access-check` — administrator-only access check
- `GET /api/v1/patients?q=&limit=20&offset=0` — search/list active patient records
- `GET /api/v1/patients/{patient_id}` — read a patient record
- `POST /api/v1/patients` — register a patient (administrator or information officer)
- `PATCH /api/v1/patients/{patient_id}` — update patient demographics
- `DELETE /api/v1/patients/{patient_id}` — soft-deactivate a patient
- `GET /api/v1/wards` and `GET /api/v1/beds` — view active wards and beds
- `POST /api/v1/wards` and `POST /api/v1/beds` — create wards/beds (administrator only)
- `GET /api/v1/admissions` — list admissions, with optional status/patient filters
- `POST /api/v1/admissions` — admit a patient and optionally reserve a bed
- `POST /api/v1/admissions/{id}/transfer` — transfer an admitted patient to an available bed
- `POST /api/v1/admissions/{id}/discharge` — discharge an admitted patient and release the bed
- `GET /api/v1/encounters` and `GET /api/v1/encounters/{id}` — list and view clinical encounters
- `POST /api/v1/encounters` — open a clinical encounter for an active patient
- `PATCH /api/v1/encounters/{id}` — update encounter notes/status and close an encounter
- `GET/POST /api/v1/encounters/{id}/vitals` — read or record vital signs
- `GET/POST /api/v1/encounters/{id}/diagnoses` — read or record encounter diagnoses
- `GET /api/v1/emergency-events` — list emergency-room events
- `POST /api/v1/emergency-events` — register an emergency event and link/create an encounter when a patient is known
- `PATCH /api/v1/emergency-events/{id}/triage` — update triage level and emergency status
- `GET/POST /api/v1/encounters/{id}/consultation-notes` — list or add doctor-authored consultation notes
- `GET/POST /api/v1/encounters/{id}/nursing-notes` — list or add nurse-authored nursing notes

## Database migration and seed
The initial schema migration must be reviewed and applied to the development Supabase project before using database endpoints. See [setup guide](../docs/setup.md). After applying it, run:

```bash
uv run python scripts/seed_demo.py
```

The seed is idempotent and uses fictional data. It creates reference data, 20 fictional patients, 15 fictional beds across two wards, and catalog items. Do not use real patient data.

## Security and current limits
All protected endpoints require a valid Supabase bearer access token and an active NexusCare profile. Role checks are enforced by FastAPI; the direct SQLAlchemy connection does not automatically inherit the user's Supabase RLS permissions. Patient list/detail access is limited to a patient's own linked record or authorized staff roles. Admission and bed operations use database row locks for key state transitions and log important changes to `audit_logs`.

This is a capstone development foundation, not yet production-ready clinical software. Department/encounter-specific staff access, lab workflows, pharmacy, billing, inventory, appointments, notifications, and full frontend integration remain to be implemented. Clinical and note endpoints are a development foundation and require further workflow/security review before real patient data is used.
