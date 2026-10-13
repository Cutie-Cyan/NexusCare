# NexusCare Role-Permission Matrix

This matrix documents the implemented role checks for the current capstone build. It is not a production authorization certification. Some endpoints still need tighter care-team, department, and encounter assignment scopes; hiding UI controls is not a security boundary.

| Capability | Admin | Info Officer | Doctor | Nurse | Cashier | Lab Staff | Pharmacy Staff | Patient |
|---|---|---|---|---|---|---|---|---|
| Staff accounts, role assignments, settings | Manage | No | No | No | No | No | No | No |
| Register/search patient | Yes | Yes | Read | Read | Billing scope | Ordered-test scope | Prescription scope | Own record |
| Patient history | Yes | Yes | Clinical view | Clinical view | Billing view | Released lab results | Prescription view | Own released/authorized history |
| Admissions, wards, beds | Manage | Manage | Read | Read/care workflow | Read-only admission data | Read-only | Read-only | Own admission/appointment scope |
| Clinical encounters and diagnoses | Read/audit | No | Create/update | View and relevant nursing workflow | No | No | No | Own authorized history |
| Vital signs and nursing notes | Read/audit | No | Read | Create | No | No | No | Own authorized history |
| Emergency triage | Read | Intake/read | Triage | Triage | No | No | No | No |
| Lab orders/results | Read | No | Order/review | Read | Billing authorization | Process/enter/verify | No | Released results through history |
| Prescriptions/dispensing | Read | No | Prescribe | Read | Billing visibility | No | Stock/dispense | Own history |
| Bills, payments, receipts, service fees | Admin/reversal | Operational view | No financial ledger access | No financial ledger access | Create/post/authorize | No | Charges via dispensing | Own bills/receipts |
| Inventory and procurement | Manage | No | No | No | No | No | Stock/request/receive | No |
| Appointments/online consultation | Manage | Schedule | Schedule/clinical session | Relevant view | No | No | No | Request/cancel own appointment and request online consultation |
| Notifications | Own inbox | Own inbox | Own inbox | Own inbox | Own inbox | Own inbox | Own inbox | Own inbox |
| Reports and audit trail | Full/admin audit | Operational summary | Clinical whiteboard | Clinical whiteboard | Financial summary | Clinical whiteboard | Stock/clinical whiteboard | Own dashboard data |

## Enforcement notes

- Supabase Auth access tokens are validated by FastAPI; role assignments come from the database, not user-editable metadata.
- Staff account provisioning is administrator-only and requires the server-only `SUPABASE_SECRET_KEY`. Bootstrap the first administrator manually using `docs/setup.md`.
- Patient accounts must be linked to exactly one patient record. Patient appointment creation/cancellation and patient-history queries are scoped to that linked record.
- Pharmacy stock and procurement operations are row-locked and audited. Lab processing requires payment for the test or an administrator/cashier-authorized billing arrangement. Discharge with an outstanding balance requires an administrator-authorized reason.
- All 43 public application tables have RLS enabled. Tables without explicit browser Data API policies are default-deny. The backend uses its own SQLAlchemy connection, so FastAPI must enforce each role and data scope itself.
- Before real-world use, add department/encounter/care-team scoping and integration tests for both permitted and denied access. See `docs/security-review.md`.
