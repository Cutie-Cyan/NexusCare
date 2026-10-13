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

## Implemented API modules

- **Authentication/admin:** `GET /api/v1/auth/me`, `GET /api/v1/admin/access-check`, administrator-only `GET /api/v1/admin/audit-logs`.
- **Patients:** `GET/POST /api/v1/patients`, `GET/PATCH/DELETE /api/v1/patients/{id}`; patient records are soft-deactivated, not hard-deleted.
- **Admissions/beds:** `GET/POST /api/v1/wards`, `GET/POST /api/v1/beds`, `GET/POST /api/v1/admissions`, `POST /api/v1/admissions/{id}/transfer`, `POST /api/v1/admissions/{id}/discharge`.
- **Clinical/emergency:** encounters, vital signs, diagnoses, emergency-event creation and triage.
- **Consultation/nursing:** append-only consultation and nursing notes per encounter.
- **Laboratory:** test catalog, lab orders, processing status, result entry, and independent result verification/release.
- **Pharmacy:** `GET/POST /api/v1/medicines`, `GET/POST /api/v1/medicine-batches`, `GET /api/v1/pharmacy/stock`, `POST /api/v1/prescriptions`, prescription listing/items, and `POST /api/v1/prescription-items/{id}/dispense`. Dispensing locks stock rows, rejects expired/mismatched batches and prevents dispensing more than prescribed.
- **Billing/payments:** service catalog, bill creation, bill items/balance, payment listing/posting, receipt creation, and administrator-only payment reversal. Payments require an `Idempotency-Key`; posted payments are reversed with an audit record rather than deleted.
- **Inventory:** supplier catalogue, inventory item management, stock movement posting, movement history, low-stock filtering. Stock changes are row-locked and cannot make quantities negative.
- **Appointments/online consultation:** appointment listing/creation/status, clinician schedule read, and online-consultation session creation.
- **Notifications/settings/reports:** per-profile notifications and read status; administrator-only system settings; role-restricted operational summary reporting.
- **Health:** `GET /api/v1/health` reports API process health only, not database or auth connectivity.

The complete interactive endpoint reference is available at `/docs` when the API is running.

## Database migration and seed
The initial schema is defined in `alembic/versions/20261010_0001_initial_schema.py`. The connected NexusCare Supabase project has already received this schema through the Supabase migration integration. **Do not run `alembic upgrade head` against that already-migrated project until its Alembic version baseline has been reconciled**; doing so may attempt to recreate existing tables. For new environments, review the migration and setup guide before applying it.

The seed is idempotent and uses fictional data. From `backend/`, run it only after configuring a valid database connection:

```bash
uv run python scripts/seed_demo.py
```

It creates reference data, 20 fictional patients, 15 fictional beds across two wards, and catalog items. Do not use real patient data. Optional Auth user seeding creates five fictional doctor accounts and requires server-only secrets; never use demo credentials in production.

## Security and limitations
All protected endpoints require a valid Supabase bearer access token and an active NexusCare profile. Role checks are enforced by FastAPI; the direct SQLAlchemy connection does not automatically inherit the signed-in user's Supabase RLS permissions. Review `docs/security-review.md` before exposing or deploying the system.

This is a capstone development foundation, not production-ready clinical software. Staff department/encounter scopes, comprehensive automated authorization tests, formal clinical validation, disaster recovery, monitoring, and security/privacy review are still required. The connected database should contain fictional demo records only.
