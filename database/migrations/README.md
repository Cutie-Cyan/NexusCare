# Database migrations

Migrations live in `backend/alembic/versions/` and are managed with Alembic through `uv`.

## Phase 2 initial migration

`20261010_0001_initial_schema.py` creates the initial SQLAlchemy model tables and enables row-level security (RLS). It also links application profiles to Supabase Auth identities. Most direct client access to clinical and financial tables is denied by default; FastAPI must perform authentication and role checks before accessing records.

From the `backend/` directory:
```bash
uv lock
uv sync
# Configure DATABASE_URL in backend/.env first.
uv run alembic upgrade head
uv run alembic current
```

Review the migration and confirm the target database before applying it. Back up any non-disposable database first. Never use `alembic downgrade` against valuable data without understanding that the initial downgrade drops the schema tables.

## Fictional seed data

After applying migrations:
```bash
uv run python scripts/seed_demo.py
```
The default run creates role definitions, departments, service/test/medicine reference rows, and 20 fictional patients. Optional doctor account creation is documented in `docs/setup.md` and requires an explicit `--create-auth-users` flag plus server-only secrets.

## Rules
- Generate and commit `backend/uv.lock` using `uv lock` in an environment with package registry access.
- Never commit credentials.
- Never seed real patient data.
- Review generated migration diffs before applying.
- Do not use `Base.metadata.create_all` as a replacement for reviewed Alembic migrations in deployed environments.
- RLS is defense in depth; backend authorization and record-ownership checks are still required.
