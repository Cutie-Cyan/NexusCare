"""Procurement requests and receiving records.

Revision ID: 20261014_0002
Revises: 20261010_0001

The matching DDL was applied to the connected Supabase project through its
migration integration. Do not run Alembic against that existing project until
the initial Alembic baseline has been reconciled.
"""
from alembic import op

revision = "20261014_0002"
down_revision = "20261010_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.procurement_requests (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_number varchar(50) NOT NULL UNIQUE,
            supplier_id uuid REFERENCES public.suppliers(id) ON DELETE SET NULL,
            requested_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
            approved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
            status varchar(30) NOT NULL DEFAULT 'draft',
            notes text,
            approved_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.procurement_items (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            request_id uuid NOT NULL REFERENCES public.procurement_requests(id) ON DELETE RESTRICT,
            inventory_item_id uuid NOT NULL REFERENCES public.inventory_items(id) ON DELETE RESTRICT,
            requested_quantity numeric(12,3) NOT NULL CHECK (requested_quantity > 0),
            received_quantity numeric(12,3) NOT NULL DEFAULT 0
                CHECK (received_quantity >= 0 AND received_quantity <= requested_quantity),
            unit_cost numeric(12,2) NOT NULL CHECK (unit_cost >= 0),
            notes text,
            CONSTRAINT uq_procurement_items_request_item UNIQUE (request_id, inventory_item_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.receiving_records (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            procurement_item_id uuid NOT NULL REFERENCES public.procurement_items(id) ON DELETE RESTRICT,
            quantity_received numeric(12,3) NOT NULL CHECK (quantity_received > 0),
            received_by uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
            supplier_reference varchar(120),
            notes text,
            received_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_procurement_requests_status ON public.procurement_requests(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_procurement_items_request_id ON public.procurement_items(request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_receiving_records_item_id ON public.receiving_records(procurement_item_id)")
    op.execute("ALTER TABLE public.procurement_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.procurement_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.receiving_records ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS public.receiving_records")
    op.execute("DROP TABLE IF EXISTS public.procurement_items")
    op.execute("DROP TABLE IF EXISTS public.procurement_requests")
