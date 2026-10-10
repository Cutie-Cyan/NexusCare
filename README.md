# Development of an Integrated Hospital Information and Resource Management System

**Project name:** NexusCare

NexusCare is a capstone project integrating patient information, clinical services, hospital resources, billing, pharmacy, laboratory services, and administration.

## Current status — Phase 2 foundation

The repository includes the Phase 1 React/Vite starter interface and FastAPI health endpoint, plus Phase 2 SQLAlchemy models, an initial Alembic schema migration, Supabase Auth token verification, database-backed role checks, RLS policies, and repeatable fictional reference/patient seed data.

**Not yet complete:** patient CRUD, admissions, consultations, nursing, emergency, laboratory, pharmacy, billing, inventory, appointments, and end-to-end workflows. The existing UI pages are still placeholders. The project has not been confirmed running against your Supabase database, and the migration has not been applied automatically.

## Stack

- Frontend: React, Vite, JavaScript, Tailwind CSS, React Router, TanStack Query, React Hook Form, Zod, Lucide React, Recharts.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2, Alembic, uv.
- Services: Supabase PostgreSQL and Supabase Auth.
- Package tools: Bun (frontend), uv (backend).

## Start here

Follow [Local Setup](docs/setup.md) before running the backend or applying database migrations. Review [Architecture](docs/architecture.md), [role permissions](docs/role-permissions.md), and [migration guidance](database/migrations/README.md).

Never commit real credentials or use real patient data during development. Do not treat this project as ready for clinical or production use without security, privacy, and workflow validation.
