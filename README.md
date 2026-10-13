# Development of an Integrated Hospital Information and Resource Management System

**Project name:** NexusCare

NexusCare is a capstone project integrating patient information, clinical services, hospital resources, billing, pharmacy, laboratory services, procurement, and administration.

## Current implementation status

The `develop` branch contains a FastAPI backend for patient records and history, admissions/wards/beds, emergency triage, clinical encounters and notes, laboratory orders/results and billing eligibility, pharmacy/prescriptions/dispensing, itemized billing/payments/receipts, inventory/procurement/receiving, appointments/online consultations, notifications, reporting, settings, staff provisioning, and audit search.

The connected Supabase project currently has **43 public tables** with RLS enabled and fictional demo reference data. The demo seed includes 20 fictional patients, 5 wards, 30 beds, service/laboratory/medicine catalogs, 2 fictional suppliers, and 3 fictional general-supply inventory items. No Auth demo accounts have been created because server-only secrets and passwords have not been configured.

The React frontend now uses Supabase Auth, a bearer-token API client, role-aware navigation, a live summary dashboard, patient search/registration/history, notification center, and read-only API tables for other modules. Dedicated create/edit/action screens for most non-patient modules are still pending.

## Stack

- Frontend: React, Vite, JavaScript, Tailwind CSS, React Router, TanStack Query, Lucide React.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic, uv.
- Services: Supabase PostgreSQL and Supabase Auth.
- Package tools: Bun (frontend), uv (backend).

## Start here

Follow [Local Setup](docs/setup.md) before running the frontend or backend. Review [Architecture](docs/architecture.md), [role permissions](docs/role-permissions.md), and [Security Review](docs/security-review.md).

**Important:** the initial schema and procurement extension have been applied through the Supabase migration integration. The local Alembic baseline still needs to be reconciled, so do not run `alembic upgrade head` against the already-migrated Supabase project yet.

Never commit real credentials or use real patient data during development. This project is not ready for real clinical or production use without further security, privacy, clinical, and workflow validation.
