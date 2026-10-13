# Development of an Integrated Hospital Information and Resource Management System

**Project name:** NexusCare

NexusCare is a capstone project integrating patient information, clinical services, hospital resources, billing, pharmacy, laboratory services, and administration.

## Current status — Phase 4 API foundation

The repository includes the React/Vite starter interface, SQLAlchemy models and initial Alembic schema, Supabase Auth token verification, database-backed role checks, fictional seed data, patient CRUD, and an initial admissions/bed-management API.

**Not yet complete:** ward transfers, clinical encounters/consultations, nursing, emergency, laboratory, pharmacy, billing, inventory, appointments, and end-to-end workflows. The UI pages are still placeholders. GitHub Actions checks run in CI, but the project has not been verified against your actual Supabase database, and the migration has not been applied automatically.

## Stack

- Frontend: React, Vite, JavaScript, Tailwind CSS, React Router, TanStack Query, React Hook Form, Zod, Lucide React, Recharts.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic, uv.
- Services: Supabase PostgreSQL and Supabase Auth.
- Package tools: Bun (frontend), uv (backend).

## Start here

Follow [Local Setup](docs/setup.md) before running the backend or applying database migrations. Review [Architecture](docs/architecture.md), [role permissions](docs/role-permissions.md), and [migration guidance](database/migrations/README.md).

Never commit real credentials or use real patient data during development. Do not treat this project as ready for clinical or production use without security, privacy, and workflow validation.
