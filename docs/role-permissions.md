# NexusCare Role-Permission Matrix (Planned)

This is the intended minimum-access policy. Enforce all permissions in FastAPI; hiding UI controls is not security.

| Capability | Admin | Info Officer | Doctor | Nurse | Cashier | Lab Staff | Pharmacy Staff | Patient |
|---|---|---|---|---|---|---|---|---|
| Staff, roles, settings | Yes | No | No | No | No | No | No | No |
| Register/search patient | Yes | Yes | Assigned scope | Assigned scope | Billing scope | Ordered-test scope | Prescription scope | Own record |
| Demographic updates | Yes | Limited | No | No | No | No | No | Limited own profile |
| Admissions/beds | Yes | Yes | Assigned view | Care workflow | No | No | No | Own status |
| Clinical notes/diagnoses | Authorized | No | Yes | Nursing notes | No | No | No | Released data only |
| Vitals/nursing care | Authorized | No | View | Yes | No | No | No | Released data only |
| Lab orders/results | Authorized | No | Order/review | Per workflow | No | Process/release | No | Released results |
| Prescriptions | Authorized | No | Create/review | View as needed | No | No | Verify/dispense | Own prescriptions |
| Billing/payments | Reports | No | Relevant summary | No | Yes | No | Allowed dispensing charges | Own billing |
| Inventory | Yes | No | No | No | No | Lab stock | Pharmacy stock | No |
| Reports/audit logs | Admin | Operational | Clinical | Nursing | Financial | Lab | Pharmacy | Own data only |
| Appointments | Admin view | Schedule | Own schedule | Relevant view | No | No | No | Own appointments |

Rules: default deny; check patient/encounter scope server-side; never trust client-supplied roles or patient IDs; never use user-editable Supabase user_metadata for authorization; patient role must be linked to its own profile; audit privileged actions; review RLS before exposing tables through Supabase Data API.
