"""Initial NexusCare schema, reference data, and row-level security.

Revision ID: 20261010_0001
Revises:
"""
from alembic import op

revision = "20261010_0001"
down_revision = None
branch_labels = None
depends_on = None

# This is deliberately frozen SQL, not Base.metadata.create_all(). Historical
# migrations must not change when current SQLAlchemy models evolve.
TABLE_DDL = [
    """CREATE TABLE public.roles (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(50) NOT NULL UNIQUE,
        name varchar(120) NOT NULL,
        description text
    )""",
    """CREATE TABLE public.departments (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(40) NOT NULL UNIQUE,
        name varchar(120) NOT NULL UNIQUE,
        description text,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.profiles (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        auth_user_id uuid NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
        full_name varchar(180) NOT NULL,
        email varchar(255),
        is_active boolean NOT NULL DEFAULT true,
        department_id uuid REFERENCES public.departments(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.user_roles (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
        role_id uuid NOT NULL REFERENCES public.roles(id) ON DELETE RESTRICT,
        assigned_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        assigned_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_user_roles_profile_role UNIQUE(profile_id, role_id)
    )""",
    """CREATE TABLE public.wards (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        department_id uuid REFERENCES public.departments(id) ON DELETE SET NULL,
        code varchar(40) NOT NULL UNIQUE,
        name varchar(120) NOT NULL,
        ward_type varchar(60) NOT NULL,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.beds (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        ward_id uuid NOT NULL REFERENCES public.wards(id) ON DELETE RESTRICT,
        bed_number varchar(30) NOT NULL,
        status varchar(30) NOT NULL DEFAULT 'available',
        notes text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_beds_ward_number UNIQUE(ward_id, bed_number)
    )""",
    """CREATE TABLE public.patients (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_profile_id uuid UNIQUE REFERENCES public.profiles(id) ON DELETE SET NULL,
        medical_record_number varchar(40) NOT NULL UNIQUE,
        first_name varchar(100) NOT NULL,
        middle_name varchar(100),
        last_name varchar(100) NOT NULL,
        date_of_birth date,
        sex varchar(30),
        phone varchar(40),
        email varchar(255),
        address text,
        emergency_contact_name varchar(180),
        emergency_contact_phone varchar(40),
        allergies text,
        notes text,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.admissions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
        bed_id uuid REFERENCES public.beds(id) ON DELETE RESTRICT,
        admitted_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        attending_doctor_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        admission_type varchar(40) NOT NULL DEFAULT 'general',
        status varchar(30) NOT NULL DEFAULT 'admitted',
        admitted_at timestamptz NOT NULL DEFAULT now(),
        discharged_at timestamptz,
        discharge_notes text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.encounters (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
        admission_id uuid REFERENCES public.admissions(id) ON DELETE SET NULL,
        department_id uuid REFERENCES public.departments(id) ON DELETE SET NULL,
        clinician_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        encounter_type varchar(40) NOT NULL DEFAULT 'consultation',
        status varchar(30) NOT NULL DEFAULT 'open',
        chief_complaint text,
        clinical_notes text,
        started_at timestamptz NOT NULL DEFAULT now(),
        ended_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.vital_signs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL REFERENCES public.encounters(id) ON DELETE CASCADE,
        recorded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        temperature_c numeric(4,1),
        pulse_bpm integer,
        respiratory_rate integer,
        systolic_bp integer,
        diastolic_bp integer,
        oxygen_saturation numeric(5,2),
        weight_kg numeric(6,2),
        height_cm numeric(6,2),
        recorded_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.diagnoses (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL REFERENCES public.encounters(id) ON DELETE CASCADE,
        code varchar(40),
        description text NOT NULL,
        is_primary boolean NOT NULL DEFAULT false,
        recorded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL
    )""",
    """CREATE TABLE public.consultations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL UNIQUE REFERENCES public.encounters(id) ON DELETE RESTRICT,
        clinician_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        assessment text,
        plan text,
        follow_up_at timestamptz,
        signed_at timestamptz
    )""",
    """CREATE TABLE public.consultation_notes (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL REFERENCES public.encounters(id) ON DELETE RESTRICT,
        author_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        note_type varchar(40) NOT NULL DEFAULT 'progress',
        content text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        amended_at timestamptz
    )""",
    """CREATE TABLE public.nursing_notes (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL REFERENCES public.encounters(id) ON DELETE RESTRICT,
        nurse_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        note_type varchar(50) NOT NULL DEFAULT 'progress',
        content text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.emergency_events (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id uuid REFERENCES public.patients(id) ON DELETE SET NULL,
        encounter_id uuid REFERENCES public.encounters(id) ON DELETE SET NULL,
        triage_level varchar(30) NOT NULL,
        chief_complaint text NOT NULL,
        status varchar(30) NOT NULL DEFAULT 'waiting',
        arrived_at timestamptz NOT NULL DEFAULT now(),
        triaged_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL
    )""",
    """CREATE TABLE public.laboratory_tests (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(50) NOT NULL UNIQUE,
        name varchar(180) NOT NULL,
        description text,
        base_fee numeric(12,2) NOT NULL DEFAULT 0.00,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.laboratory_orders (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL REFERENCES public.encounters(id) ON DELETE RESTRICT,
        test_id uuid NOT NULL REFERENCES public.laboratory_tests(id) ON DELETE RESTRICT,
        ordered_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        status varchar(30) NOT NULL DEFAULT 'ordered',
        priority varchar(20) NOT NULL DEFAULT 'routine',
        clinical_notes text,
        ordered_at timestamptz NOT NULL DEFAULT now(),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.laboratory_results (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        order_id uuid NOT NULL UNIQUE REFERENCES public.laboratory_orders(id) ON DELETE RESTRICT,
        result_text text,
        result_data jsonb,
        entered_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        verified_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        status varchar(30) NOT NULL DEFAULT 'draft',
        entered_at timestamptz NOT NULL DEFAULT now(),
        released_at timestamptz
    )""",
    """CREATE TABLE public.medicines (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(50) NOT NULL UNIQUE,
        name varchar(180) NOT NULL,
        strength varchar(80),
        dosage_form varchar(80),
        reorder_level integer NOT NULL DEFAULT 0,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.medicine_batches (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        medicine_id uuid NOT NULL REFERENCES public.medicines(id) ON DELETE RESTRICT,
        batch_number varchar(80) NOT NULL,
        quantity_on_hand integer NOT NULL DEFAULT 0,
        unit_cost numeric(12,2) NOT NULL DEFAULT 0.00,
        selling_price numeric(12,2) NOT NULL DEFAULT 0.00,
        expires_on date,
        CONSTRAINT uq_medicine_batch_number UNIQUE(medicine_id, batch_number)
    )""",
    """CREATE TABLE public.prescriptions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        encounter_id uuid NOT NULL REFERENCES public.encounters(id) ON DELETE RESTRICT,
        prescribed_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        status varchar(30) NOT NULL DEFAULT 'issued',
        instructions text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.prescription_items (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        prescription_id uuid NOT NULL REFERENCES public.prescriptions(id) ON DELETE CASCADE,
        medicine_id uuid NOT NULL REFERENCES public.medicines(id) ON DELETE RESTRICT,
        dose varchar(120) NOT NULL,
        route varchar(80),
        frequency varchar(120) NOT NULL,
        duration varchar(120),
        quantity integer NOT NULL,
        instructions text
    )""",
    """CREATE TABLE public.pharmacy_dispensing (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        prescription_item_id uuid NOT NULL REFERENCES public.prescription_items(id) ON DELETE RESTRICT,
        medicine_batch_id uuid NOT NULL REFERENCES public.medicine_batches(id) ON DELETE RESTRICT,
        quantity integer NOT NULL,
        dispensed_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        dispensed_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.suppliers (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(50) NOT NULL UNIQUE,
        name varchar(180) NOT NULL,
        contact_name varchar(180),
        phone varchar(40),
        email varchar(255),
        address text,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.inventory_items (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(50) NOT NULL UNIQUE,
        name varchar(180) NOT NULL,
        category varchar(80) NOT NULL,
        unit varchar(40) NOT NULL DEFAULT 'piece',
        quantity_on_hand numeric(12,3) NOT NULL DEFAULT 0,
        reorder_level numeric(12,3) NOT NULL DEFAULT 0,
        unit_cost numeric(12,2) NOT NULL DEFAULT 0.00,
        supplier_id uuid REFERENCES public.suppliers(id) ON DELETE SET NULL,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.inventory_item_transactions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        item_id uuid NOT NULL REFERENCES public.inventory_items(id) ON DELETE RESTRICT,
        quantity_delta numeric(12,3) NOT NULL,
        transaction_type varchar(40) NOT NULL,
        reference_id uuid,
        recorded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        notes text,
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.inventory_transactions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        medicine_batch_id uuid NOT NULL REFERENCES public.medicine_batches(id) ON DELETE RESTRICT,
        quantity_delta integer NOT NULL,
        transaction_type varchar(40) NOT NULL,
        reference_id uuid,
        recorded_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        notes text,
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.service_catalog (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        code varchar(50) NOT NULL UNIQUE,
        name varchar(180) NOT NULL,
        category varchar(80) NOT NULL,
        price numeric(12,2) NOT NULL,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.bills (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
        encounter_id uuid REFERENCES public.encounters(id) ON DELETE SET NULL,
        bill_number varchar(50) NOT NULL UNIQUE,
        status varchar(30) NOT NULL DEFAULT 'open',
        subtotal numeric(12,2) NOT NULL DEFAULT 0.00,
        adjustments numeric(12,2) NOT NULL DEFAULT 0.00,
        total numeric(12,2) NOT NULL DEFAULT 0.00,
        created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.bill_items (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        bill_id uuid NOT NULL REFERENCES public.bills(id) ON DELETE RESTRICT,
        service_id uuid REFERENCES public.service_catalog(id) ON DELETE SET NULL,
        description varchar(240) NOT NULL,
        quantity integer NOT NULL DEFAULT 1,
        unit_price numeric(12,2) NOT NULL,
        line_total numeric(12,2) NOT NULL
    )""",
    """CREATE TABLE public.payments (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        bill_id uuid NOT NULL REFERENCES public.bills(id) ON DELETE RESTRICT,
        receipt_number varchar(50) NOT NULL UNIQUE,
        idempotency_key varchar(120) NOT NULL UNIQUE,
        amount numeric(12,2) NOT NULL,
        payment_method varchar(40) NOT NULL,
        status varchar(30) NOT NULL DEFAULT 'posted',
        received_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        received_at timestamptz NOT NULL DEFAULT now(),
        reversed_at timestamptz,
        reversal_reason text
    )""",
    """CREATE TABLE public.payment_allocations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        payment_id uuid NOT NULL REFERENCES public.payments(id) ON DELETE RESTRICT,
        bill_item_id uuid NOT NULL REFERENCES public.bill_items(id) ON DELETE RESTRICT,
        amount numeric(12,2) NOT NULL
    )""",
    """CREATE TABLE public.receipts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        payment_id uuid NOT NULL UNIQUE REFERENCES public.payments(id) ON DELETE RESTRICT,
        receipt_number varchar(50) NOT NULL UNIQUE,
        issued_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        issued_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.ward_transfers (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        admission_id uuid NOT NULL REFERENCES public.admissions(id) ON DELETE RESTRICT,
        from_bed_id uuid REFERENCES public.beds(id) ON DELETE RESTRICT,
        to_bed_id uuid NOT NULL REFERENCES public.beds(id) ON DELETE RESTRICT,
        requested_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
        reason text,
        status varchar(30) NOT NULL DEFAULT 'completed',
        transferred_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.appointments (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        patient_id uuid NOT NULL REFERENCES public.patients(id) ON DELETE RESTRICT,
        department_id uuid REFERENCES public.departments(id) ON DELETE SET NULL,
        clinician_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        scheduled_at timestamptz NOT NULL,
        status varchar(30) NOT NULL DEFAULT 'scheduled',
        reason text,
        created_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.online_consultations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        appointment_id uuid NOT NULL UNIQUE REFERENCES public.appointments(id) ON DELETE RESTRICT,
        meeting_url text,
        status varchar(30) NOT NULL DEFAULT 'scheduled',
        started_at timestamptz,
        ended_at timestamptz
    )""",
    """CREATE TABLE public.doctor_schedules (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        doctor_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
        department_id uuid REFERENCES public.departments(id) ON DELETE SET NULL,
        weekday integer NOT NULL,
        start_time varchar(5) NOT NULL,
        end_time varchar(5) NOT NULL,
        is_active boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.system_settings (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        setting_key varchar(120) NOT NULL UNIQUE,
        setting_value jsonb NOT NULL DEFAULT '{}'::jsonb,
        description text,
        updated_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.notifications (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        recipient_profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
        title varchar(180) NOT NULL,
        message text NOT NULL,
        category varchar(60) NOT NULL DEFAULT 'general',
        read_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE public.audit_logs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        actor_profile_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
        action varchar(100) NOT NULL,
        resource_type varchar(100) NOT NULL,
        resource_id varchar(100),
        details jsonb,
        ip_address varchar(64),
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
]

INDEX_DDL = [
    "CREATE INDEX ix_profiles_auth_user_id ON public.profiles(auth_user_id)",
    "CREATE INDEX ix_profiles_email ON public.profiles(email)",
    "CREATE INDEX ix_patients_name_search ON public.patients(last_name, first_name)",
    "CREATE INDEX ix_admissions_patient_id ON public.admissions(patient_id)",
    "CREATE INDEX ix_admissions_status ON public.admissions(status)",
    "CREATE INDEX ix_encounters_patient_id ON public.encounters(patient_id)",
    "CREATE INDEX ix_encounters_status ON public.encounters(status)",
    "CREATE INDEX ix_vital_signs_encounter_id ON public.vital_signs(encounter_id)",
    "CREATE INDEX ix_diagnoses_encounter_id ON public.diagnoses(encounter_id)",
    "CREATE INDEX ix_laboratory_orders_encounter_id ON public.laboratory_orders(encounter_id)",
    "CREATE INDEX ix_laboratory_orders_status ON public.laboratory_orders(status)",
    "CREATE INDEX ix_medicines_name ON public.medicines(name)",
    "CREATE INDEX ix_medicine_batches_medicine_id ON public.medicine_batches(medicine_id)",
    "CREATE INDEX ix_prescriptions_encounter_id ON public.prescriptions(encounter_id)",
    "CREATE INDEX ix_prescription_items_prescription_id ON public.prescription_items(prescription_id)",
    "CREATE INDEX ix_inventory_transactions_medicine_batch_id ON public.inventory_transactions(medicine_batch_id)",
    "CREATE INDEX ix_inventory_item_transactions_item_id ON public.inventory_item_transactions(item_id)",
    "CREATE INDEX ix_notifications_recipient_profile_id ON public.notifications(recipient_profile_id)",
    "CREATE INDEX ix_audit_logs_action ON public.audit_logs(action)",
    "CREATE INDEX ix_bills_patient_id ON public.bills(patient_id)",
    "CREATE INDEX ix_bills_status ON public.bills(status)",
    "CREATE INDEX ix_bill_items_bill_id ON public.bill_items(bill_id)",
    "CREATE INDEX ix_payments_bill_id ON public.payments(bill_id)",
    "CREATE INDEX ix_ward_transfers_admission_id ON public.ward_transfers(admission_id)",
    "CREATE INDEX ix_appointments_patient_id ON public.appointments(patient_id)",
    "CREATE INDEX ix_appointments_scheduled_at ON public.appointments(scheduled_at)",
    "CREATE INDEX ix_appointments_status ON public.appointments(status)",
    "CREATE INDEX ix_doctor_schedules_doctor_id ON public.doctor_schedules(doctor_id)",
    "CREATE INDEX ix_emergency_events_patient_id ON public.emergency_events(patient_id)",
    "CREATE INDEX ix_emergency_events_status ON public.emergency_events(status)",
]

TABLE_NAMES = [
    "roles", "departments", "profiles", "user_roles", "wards", "beds", "patients",
    "admissions", "encounters", "vital_signs", "diagnoses", "consultations",
    "consultation_notes", "nursing_notes", "emergency_events", "laboratory_tests",
    "laboratory_orders", "laboratory_results", "medicines", "medicine_batches",
    "prescriptions", "prescription_items", "pharmacy_dispensing", "suppliers",
    "inventory_items", "inventory_item_transactions", "inventory_transactions",
    "service_catalog", "bills", "bill_items", "payments", "payment_allocations",
    "receipts", "ward_transfers", "appointments", "online_consultations",
    "doctor_schedules", "system_settings", "notifications", "audit_logs",
]


def upgrade() -> None:
    for statement in TABLE_DDL:
        op.execute(statement)
    for statement in INDEX_DDL:
        op.execute(statement)

    # RLS is enabled for every application table. A table without an explicit
    # policy is closed to direct Supabase client access by default.
    for table in TABLE_NAMES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY profiles_select_self ON public.profiles
        FOR SELECT TO authenticated USING (auth_user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY roles_select_authenticated ON public.roles
        FOR SELECT TO authenticated USING (true)
    """)
    op.execute("""
        CREATE POLICY user_roles_select_self ON public.user_roles
        FOR SELECT TO authenticated USING (
            EXISTS (
                SELECT 1 FROM public.profiles p
                WHERE p.id = user_roles.profile_id AND p.auth_user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY patients_access_authorized_roles ON public.patients
        FOR ALL TO authenticated USING (
            EXISTS (
                SELECT 1
                FROM public.profiles p
                JOIN public.user_roles ur ON ur.profile_id = p.id
                JOIN public.roles r ON r.id = ur.role_id
                WHERE p.auth_user_id = auth.uid()
                  AND p.is_active = true
                  AND (
                    r.code IN (
                      'administrator','information_officer','doctor','nurse',
                      'cashier','laboratory_staff','pharmacy_staff'
                    )
                    OR (r.code = 'patient' AND patients.patient_profile_id = p.id)
                  )
            )
        ) WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.profiles p
                JOIN public.user_roles ur ON ur.profile_id = p.id
                JOIN public.roles r ON r.id = ur.role_id
                WHERE p.auth_user_id = auth.uid()
                  AND p.is_active = true
                  AND (
                    r.code IN (
                      'administrator','information_officer','doctor','nurse',
                      'cashier','laboratory_staff','pharmacy_staff'
                    )
                    OR (r.code = 'patient' AND patients.patient_profile_id = p.id)
                  )
            )
        )
    """)
    op.execute("""
        CREATE POLICY notifications_access_self ON public.notifications
        FOR ALL TO authenticated USING (
            recipient_profile_id IN (
                SELECT p.id FROM public.profiles p WHERE p.auth_user_id = auth.uid()
            )
        ) WITH CHECK (
            recipient_profile_id IN (
                SELECT p.id FROM public.profiles p WHERE p.auth_user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY audit_logs_select_admin ON public.audit_logs
        FOR SELECT TO authenticated USING (
            EXISTS (
                SELECT 1 FROM public.profiles p
                JOIN public.user_roles ur ON ur.profile_id = p.id
                JOIN public.roles r ON r.id = ur.role_id
                WHERE p.auth_user_id = auth.uid() AND r.code = 'administrator'
            )
        )
    """)


def downgrade() -> None:
    # Destructive by design: this initial migration's downgrade drops its tables.
    for table in reversed(TABLE_NAMES):
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE")
