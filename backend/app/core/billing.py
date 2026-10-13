from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bill, BillItem


def add_service_charge(
    db: Session,
    patient_id,
    encounter_id,
    description: str,
    unit_price: Decimal,
    quantity: int = 1,
    service_id=None,
) -> Bill | None:
    """Add a service charge to the encounter's open bill, creating one if needed.

    A zero-price service is recorded in its clinical module but does not create
    a zero-value bill line. Callers must execute this inside their transaction.
    """
    if unit_price <= 0 or quantity <= 0:
        return None

    bill = db.scalar(
        select(Bill)
        .where(
            Bill.patient_id == patient_id,
            Bill.encounter_id == encounter_id,
            Bill.status.in_(["open", "partially_paid"]),
        )
        .order_by(Bill.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if bill is None:
        bill = Bill(
            patient_id=patient_id,
            encounter_id=encounter_id,
            bill_number=f"BILL-{uuid4().hex[:12].upper()}",
            status="open",
            subtotal=Decimal("0.00"),
            adjustments=Decimal("0.00"),
            total=Decimal("0.00"),
        )
        db.add(bill)
        db.flush()

    line_total = unit_price * quantity
    db.add(BillItem(
        bill_id=bill.id,
        service_id=service_id,
        description=description[:240],
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
    ))
    bill.subtotal += line_total
    bill.total = bill.subtotal + bill.adjustments
    if bill.total < 0:
        raise ValueError("Service charge would make the bill total negative.")
    if bill.status == "paid":
        bill.status = "open"
    return bill
