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
- `GET /api/v1/laboratory-tests` — list active laboratory tests (authorized clinical/lab roles)
- `POST /api/v1/laboratory-tests` — add a catalog test (administrator)
- `GET /api/v1/laboratory-orders` — list and filter laboratory orders
- `POST /api/v1/laboratory-orders` — order a test for an open encounter (doctor)
- `PATCH /api/v1/laboratory-orders/{id}/status` — update specimen/processing status (laboratory staff)
- `GET/POST /api/v1/laboratory-orders/{id}/result` — read or enter a result (laboratory staff can enter)
- `POST /api/v1/laboratory-orders/{id}/verify-result` — verify/release a result; a different staff member must verify it

## Database migration and seed
The initial schema is defined in `alembic/versions/20261010_0001_initial_schema.py`. The connected NexusCare Supabase project has already received this schema through the Supabase migration integration. **Do not run `alembic upgrade head` against that already-migrated project until its Alembic version baseline has been reconciled**; doing so may attempt to recreate existing tables. For new environments, review the migration and setup guide before applying it.

The seed is idempotent and uses fictional data. From `backend/`, run it only after configuring a valid database connection:

```bash
uv run python scripts/seed_demo.py
```

It creates reference data, 20 fictional patients, 15 fictional beds across two wards, and catalog items. Do not use real patient data. Optional Auth user seeding creates five fictional doctor accounts and requires server-only secrets; never use demo credentials in production.

## Security and current limits
All protected endpoints require a valid Supabase bearer access token and an active NexusCare profile. Role checks are enforced by FastAPI; the direct SQLAlchemy connection does not automatically inherit the user's Supabase RLS permissions. Patient list/detail access is limited to a patient's own linked record or authorized staff roles. Admission and bed operations use database row locks for key state transitions and log important changes to `audit_logs`.

Laboratory result entry is append-only in this phase: results cannot be edited or deleted through the API, and a different laboratory staff member must verify/release a draft result. Result release and order completion are recorded in the audit log. This is a capstone development foundation, not production-ready clinical software. Department/encounter-specific staff access, pharmacy, billing, inventory, appointments, notifications, analytics, and full frontend integration remain to be implemented. Do not use real patient data.
