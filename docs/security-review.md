# NexusCare Security Review

**Status:** development review; not a production security certification.

## Implemented safeguards
- Supabase Auth bearer tokens are validated server-side; the API does not trust client-provided role claims.
- Protected routes require an active NexusCare profile and check role assignments from the database.
- Patient list/detail and selected patient-owned workflows apply profile-to-patient scoping.
- Admissions and beds use row locks for bed assignment/transfer/discharge.
- Pharmacy dispensing locks the prescription item and stock batch, checks medicine match and expiry, enforces remaining prescribed quantity, and writes a stock ledger entry.
- Inventory movements use row locks and reject stock values below zero.
- Payments use exact decimal amounts, an idempotency key, a separate receipt record, and administrator-only audited reversals. Posted payments are not deleted.
- Lab results are append-only through the API and require a different laboratory staff member to verify/release.
- Sensitive create/update operations write audit records.
- Browser configuration uses only Supabase URL/publishable key; server secrets and the Postgres connection string belong in backend-only environment variables.

## Supabase RLS status and architecture
The connected Supabase project has RLS enabled on all 43 application tables. The initial migration defines a small set of explicit policies; many tables intentionally have no table-specific policy and therefore remain inaccessible through the Supabase Data API by default.

The FastAPI backend connects to Postgres using its own database credentials. SQLAlchemy queries through that connection do **not** automatically inherit the signed-in user's Supabase RLS identity. Therefore:
1. Use Supabase Auth from the browser, then call FastAPI with the access token.
2. Do not expose clinical, financial, inventory, or staff tables directly through browser Supabase queries.
3. Enforce RBAC and patient/encounter scope in every API endpoint.
4. If direct Supabase Data API access is later required, design and test explicit least-privilege RLS policies first; do not add broad authenticated-user policies just to make the UI work.

## Known gaps before any real-world use
- Some clinical and operational staff endpoints still have broad role-level access rather than assignment-, department-, encounter-, or care-team-specific scope.
- The frontend has read-only data tables for most modules; most write workflows still require the API documentation until dedicated forms are completed.
- Staff provisioning is administrator-only and requires the server-only Supabase secret key. A first administrator must be bootstrapped manually before that endpoint can be used.
- The procurement extension adds three RLS-enabled tables with no browser Data API policies; this is default-deny and intentional.
- Appointment overlap checks currently prevent exact same-time clinician duplicates but do not model appointment duration or complete schedule availability.
- Not every endpoint has full integration tests for role denial, patient ownership, concurrent writes, and database failure paths.
- The audit log is queryable by administrators, but log retention, tamper resistance, alerting, and access monitoring need operational design.
- Production deployment needs TLS, secret rotation, database backups and restore tests, monitoring, rate limits, security headers, dependency scanning, incident response, and a privacy/legal review appropriate to the deployment jurisdiction.
- Clinical workflows and decision support require validation by qualified clinical stakeholders. This project is not certified for real patient care.

## Safe development checklist
- Keep only fictional demo records in the current project.
- Keep `.env` and `.env.local` out of Git.
- Never use `SUPABASE_SECRET_KEY`, service-role keys, or database passwords in the frontend.
- Reconcile the local Alembic baseline before running migrations against the already-migrated Supabase project.
- Test with separate accounts for all eight roles and verify both allowed and denied operations.
- Review API docs and audit events after each workflow change.
