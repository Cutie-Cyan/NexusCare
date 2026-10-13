# Development of an Integrated Hospital Information and Resource Management System

**Project name:** NexusCare

NexusCare is a capstone project integrating patient information, clinical services, hospital resources, billing, pharmacy, laboratory services, procurement, and administration.

## Current implementation status

The `develop` branch contains a FastAPI backend for authentication/RBAC, patient demographics and history, admissions/wards/beds, emergency triage, encounters/vitals/diagnoses, consultation and nursing notes, laboratory orders/results/release, prescriptions/dispensing, itemized billing/payments/receipts, service fees, inventory/procurement/receiving, appointments/online consultations, notifications, whiteboard metrics, reporting, system settings, staff provisioning, and audit search.

The connected Supabase project has **43 public tables** with RLS enabled and fictional demo reference data. The seed currently includes 20 fictional patients, 9 departments, 5 wards, 30 beds, service/laboratory/medicine catalogs, 2 fictional suppliers, and 3 fictional general-supply inventory items. No Auth demo accounts have been created. A first administrator must be bootstrapped manually; see [Local Setup](docs/setup.md).

The React frontend includes Supabase Auth, role-aware navigation, a live dashboard and ward whiteboard, patient registration/edit/history, admissions and bed workflows, clinical and nursing workflows, emergency triage, lab result processing, pharmacy dispensing, inventory, procurement, appointments/online consultations, billing/payments/receipts, service fees, staff provisioning, department listing, reporting, audit search, and settings editing. Some module tables remain read-only views; see [Phase Status](docs/phase-status.md) for the implemented scope and remaining work.

## Stack

- Frontend: React, Vite, JavaScript, Tailwind CSS, React Router, TanStack Query, Lucide React.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic, uv.
- Services: Supabase PostgreSQL and Supabase Auth.
- Package tools: Bun (frontend), uv (backend).

## Start here

Follow [Local Setup](docs/setup.md). Review [Architecture](docs/architecture.md), [role permissions](docs/role-permissions.md), [Security Review](docs/security-review.md), and [Phase Status](docs/phase-status.md).

**Important:** the schema was applied through the Supabase migration integration. The local Alembic baseline still needs reconciliation, so do not run `alembic upgrade head` against the already-migrated Supabase project yet.

Never commit real credentials or use real patient data during development. This project is not ready for real clinical or production use without further security, privacy, clinical, and workflow validation.
