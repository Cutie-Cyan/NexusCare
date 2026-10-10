"""Initial NexusCare schema, reference data, and row-level security.

Revision ID: 20261010_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.models import Base

revision = "20261010_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy models are the source of truth for the initial public schema.
    Base.metadata.create_all(bind=op.get_bind())

    # Restrict profile access to the signed-in user. Staff access to patient records
    # is mediated by FastAPI role checks; direct client reads require a permitted role.
    op.execute("ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.admissions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.encounters ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.vital_signs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.diagnoses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.laboratory_orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.laboratory_results ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.prescriptions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.prescription_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.bills ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.bill_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY profiles_select_self ON public.profiles
        FOR SELECT TO authenticated USING (auth_user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY profiles_update_self ON public.profiles
        FOR UPDATE TO authenticated USING (auth_user_id = auth.uid())
        WITH CHECK (auth_user_id = auth.uid())
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
                  AND r.code IN (
                    'administrator','information_officer','doctor','nurse',
                    'cashier','laboratory_staff','pharmacy_staff','patient'
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
                  AND r.code IN (
                    'administrator','information_officer','doctor','nurse',
                    'cashier','laboratory_staff','pharmacy_staff','patient'
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

    # Direct client table access stays closed by default for sensitive clinical and
    # financial tables. The API must apply authorization before using server DB credentials.
    for table in (
        "admissions", "encounters", "vital_signs", "diagnoses",
        "laboratory_orders", "laboratory_results", "prescriptions",
        "prescription_items", "bills", "bill_items", "payments",
    ):
        op.execute(
            f"CREATE POLICY {table}_deny_direct_client_access ON public.{table} "
            "FOR ALL TO authenticated USING (false) WITH CHECK (false)"
        )


def downgrade() -> None:
    for table in (
        "profiles", "roles", "user_roles", "patients", "admissions", "encounters",
        "vital_signs", "diagnoses", "laboratory_orders", "laboratory_results",
        "prescriptions", "prescription_items", "bills", "bill_items", "payments",
        "audit_logs", "notifications",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_select_self ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_self ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_access_authorized_roles ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_deny_direct_client_access ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select_admin ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select_authenticated ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_access_self ON public.{table}")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
    Base.metadata.drop_all(bind=op.get_bind())
