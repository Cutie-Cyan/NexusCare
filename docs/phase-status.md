# NexusCare Phase Status

This is the implementation tracker for the development phases. “Implemented” means code is present in the repository; it does not mean the workflow has been validated for real clinical use.

| Phase | Scope | Status |
|---|---|---|
| 1 | Repository foundation, documentation, React/Vite shell, FastAPI health endpoint | Implemented |
| 2 | SQLAlchemy models, initial schema, auth verification, RBAC dependencies, fictional seed, CI | Implemented; live Supabase migration applied; local Alembic baseline still needs reconciliation |
| 3 | Patient search, registration, updates, soft deactivation, audit trail | Implemented; frontend registration/edit screens added |
| 4 | Departments, wards/beds, admission, transfer, discharge and billing exception handling | Implemented; ward occupancy overview and UI workflow present |
| 5 | Clinical encounters, vitals, diagnoses, emergency events and triage | Implemented |
| 6 | Append-only consultation and nursing notes | Implemented |
| 7 | Laboratory catalog, orders, status workflow, result entry and independent release | Implemented |
| 8 | Medicine catalog/batches, prescriptions, dispensing, stock ledger, pharmacy charges | Implemented |
| 9 | Service fees, bill items, payment idempotency, receipts, audited reversals and service charges | Implemented |
| 10 | Inventory, suppliers, procurement approvals/receiving, appointments, online consultation, notifications, settings, reports | Implemented at API level; core forms/screens are present |
| 11 | Audit search, staff/role management, billing-aware discharge controls, security review | Implemented; comprehensive authorization integration testing remains |
| 12 | Supabase login, API bearer client, role-aware navigation, dashboard, patient history, workflow pages | Implemented foundation; several non-patient lists remain read-only and need workflow-specific refinement |

## Remaining before capstone demonstration

1. Configure local environment variables and bootstrap one administrator account.
2. Reconcile Alembic's local version baseline safely before applying any future migration to the existing Supabase database.
3. Pull the latest `develop` branch and run backend tests plus frontend production build on a machine with network access.
4. Test every workflow using separate fictional accounts for all eight roles, including forbidden access and patient ownership checks.
5. Refine remaining read-only tables into focused screens, including department administration and receipt/print views where required.
6. Verify every cross-module flow end to end: registration → encounter → lab request → charge/payment eligibility → result release; prescription → dispensing → stock update → bill; stock threshold → procurement → approval → receiving; admission → bed occupancy → discharge/billing check; service → bill → payment → receipt.
7. Complete clinical, privacy, security, backup/recovery, and deployment reviews before any use beyond a fictional capstone demo.

## Scope safeguards

- Use fictional data only.
- This is a hospital information-management prototype, not a clinical decision system.
- Do not implement real payment gateways, PhilHealth claims, AI diagnosis, or a replacement for official procurement procedures.
- Keep privileged Supabase and database secrets server-side.
