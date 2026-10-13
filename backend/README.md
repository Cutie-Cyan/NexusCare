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

- **Authentication/admin:** `GET /api/v1/auth/me`; administrator-only staff creation, role replacement, activation/deactivation, access check, and audit-log search. Staff provisioning requires server-only `SUPABASE_SECRET_KEY`.
- **Patients:** `GET/POST /api/v1/patients`, `GET/PATCH/DELETE /api/v1/patients/{id}`, and role-scoped `GET /api/v1/patients/{id}/history`; patient records are soft-deactivated, not hard-deleted.
- **Admissions/beds:** department, ward, and bed management; admission, transfer, discharge, and discharge settlement/administrator-exception checks.
- **Clinical/emergency:** encounters, vital signs, diagnoses, emergency-event creation and triage.
- **Consultation/nursing:** append-only consultation and nursing notes per encounter.
- **Laboratory:** test catalog, lab orders, automatic bill charges, payment or cashier/administrator-authorized billing arrangement before processing, result entry, and independent result verification/release.
- **Pharmacy:** `GET/POST /api/v1/medicines`, `GET/POST /api/v1/medicine-batches`, `GET /api/v1/pharmacy/stock`, `POST /api/v1/prescriptions`, prescription listing/items, and `POST /api/v1/prescription-items/{id}/dispense`. Dispensing locks stock rows, rejects expired/mismatched batches and prevents dispensing more than prescribed.
- **Billing/payments:** service-fee administration, automatic professional/laboratory/pharmacy charges, bill creation/items/balance, payment listing/posting, receipt history, and administrator-only payment reversal. Payments require an `Idempotency-Key`; posted payments are reversed with an audit record rather than deleted.
- **Inventory/procurement:** suppliers, inventory items/movements, low-stock alerts, procurement request submission/approval, receiving records, and automatic stock ledger updates. Stock changes are row-locked and cannot make quantities negative.
- **Appointments/online consultation:** patient-owned appointment requests/cancellation, clinician schedule management, online consultation request/lifecycle/history.
- **Notifications/settings/reports:** workflow-generated role notifications, per-profile unread/read status, privacy-conscious whiteboard summary, administrator-only system settings, and role-restricted operational reports.
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
