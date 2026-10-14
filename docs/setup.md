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
git pull origin develop
```

## Frontend
From the repository root:

```bash
cd frontend
bun install
cp .env.example .env.local
```

Set the public project URL and publishable key in `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_SUPABASE_URL=https://icahywfnfoeevsfdepca.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
```

Only use the Supabase URL and publishable key in the browser. **Never put the database password, service-role key, or Supabase secret key in a `VITE_*` variable.** Restart Vite after changing environment variables.

Start the frontend:

```bash
bun run dev
```

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
- Interactive API docs: http://127.0.0.1:8000/docs
- Frontend: normally http://127.0.0.1:5173

## Bootstrap the first administrator

The staff-provisioning API is administrator-only, so one initial administrator profile must be linked manually after creating an Auth user:

1. In Supabase Dashboard → Authentication → Users, create a development administrator account and confirm its email. Copy the Auth user UUID.
2. In SQL Editor, replace the placeholder UUID and email in this statement, then run it:

```sql
INSERT INTO public.profiles (auth_user_id, full_name, email, department_id, is_active)
SELECT 'REPLACE_WITH_AUTH_USER_UUID'::uuid, 'NexusCare Administrator', 'admin@example.test', d.id, true
FROM public.departments d WHERE d.code = 'ADMIN'
ON CONFLICT (auth_user_id) DO UPDATE
SET full_name = EXCLUDED.full_name, email = EXCLUDED.email, department_id = EXCLUDED.department_id, is_active = true;

INSERT INTO public.user_roles (profile_id, role_id, assigned_by)
SELECT p.id, r.id, p.id
FROM public.profiles p CROSS JOIN public.roles r
WHERE p.email = 'admin@example.test' AND r.code = 'administrator'
AND NOT EXISTS (SELECT 1 FROM public.user_roles ur WHERE ur.profile_id = p.id AND ur.role_id = r.id);
```

3. Add the server-only `SUPABASE_SECRET_KEY` to `backend/.env` if you want to create additional accounts through `POST /api/v1/admin/staff`. Never expose it in the frontend.

Use a secure password, do not reuse personal credentials, and do not create real patient records. Staff account provisioning currently does not force a password change at first login; plan a secure reset flow before production.

## Database migration
The initial schema in `backend/alembic/versions/20261010_0001_initial_schema.py` has already been applied to the connected NexusCare Supabase project through the Supabase migration integration. The migration appears in Supabase migration history and the 43 public tables exist with RLS enabled, including the procurement and receiving extension.

**Important:** do not run `uv run alembic upgrade head` against that existing project yet. The schema was applied through Supabase's migration tool, and the local Alembic version table has not been reconciled; running Alembic may attempt to create tables that already exist. We will establish a safe baseline before using Alembic for future schema changes.

For a fresh development database, review the migration and target project carefully before applying it. Do not run schema changes against production without a backup and review.

## Fictional demo data
After the database connection is configured and the migration baseline is confirmed, the seed command is:

```bash
uv run python scripts/seed_demo.py
```

This idempotently seeds role and department reference records, service/lab/medicine catalog items, 20 fictional patients, nine departments, five wards, 30 fictional beds, two fictional suppliers, and three general-supply inventory items with ledger entries. No real patient information should be used.

Optional: create five fictional doctor accounts only if you intentionally want them in the Supabase Auth project. Set server-only `SUPABASE_SECRET_KEY` and a development-only `SEED_DOCTOR_PASSWORD` (at least 12 characters) in `backend/.env`, then run `uv run python scripts/seed_demo.py --create-auth-users`. Never use demo credentials in production.

## Current implementation status
- Phase 1: repository scaffolding and documentation.
- Phase 2: schema/migration foundation, Supabase Auth verification, RBAC dependency, fictional seed script.
- Phase 3: patient registration, search, retrieval, demographic update, soft deactivation.
- Phase 4: ward/bed management, admission, bed transfer, discharge, audit logging.
- Phase 5: emergency triage, clinical encounters, vital signs, diagnoses, and audit events.
- Phase 6: append-only consultation and nursing notes.
- Phase 7: lab catalog, orders, processing, results, independent verification/release.
- Phase 8: medicine catalog/batches, prescriptions, safe dispensing, stock ledger, and automatic pharmacy charges.
- Phase 9: bills, service-fee administration, automatic lab/professional/pharmacy charges, idempotent payments, receipts, and audited reversals.
- Phase 10: inventory/suppliers, procurement approvals and receiving, appointments/online consultations, notifications, whiteboard summary, settings, and reports.
- Phase 11: administrator audit search, staff provisioning/role management, billing-aware discharge exceptions, and documented RLS/RBAC review.
- Phase 12: Supabase sign-in, role-aware navigation, authenticated API client, live dashboards and notifications, plus workflows for patient history/registration, admissions, ward/bed occupancy, departments, clinical notes/vitals, emergency triage, laboratory results, pharmacy/dispensing, inventory, procurement, appointments, billing/payments, service fees, staff provisioning/role/status management, receipts, reports, audit search, and system settings. Targeted department/care-team scoping has been added to clinical encounters, notes, laboratory, emergency, prescription, and appointment workflows. A broader route audit and live end-to-end integration tests with separate role accounts remain required.

## Security note
Direct SQLAlchemy access does not automatically enforce Supabase RLS based on the signed-in user. FastAPI role checks currently protect these routes, but staff access must be tightened to department/encounter-specific scopes before production. See `docs/security-review.md`. Do not use real patient data.
