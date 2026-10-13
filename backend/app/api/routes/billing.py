from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.core.notifications import notify_roles
from app.models import (
    AuditLog, Bill, BillItem, Encounter, Patient, Payment, PaymentAllocation,
    Profile, Receipt, ServiceCatalog,
)
from app.schemas.billing import (
    BillBalanceRead, BillCreate, BillItemRead, BillRead, PaymentCreate,
    PaymentRead, PaymentReversal, ServiceCatalogCreate, ServiceCatalogUpdate,
)

router = APIRouter(tags=["billing and payments"])
BILL_READ_ROLES = {"administrator", "information_officer", "doctor", "nurse", "cashier"}
BILL_WRITE_ROLES = ("administrator", "cashier")


def _audit(db: Session, profile: Profile, action: str, kind: str, resource_id: UUID, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id, action=action, resource_type=kind,
        resource_id=str(resource_id), details=details or {},
    ))


def _posted_paid(db: Session, bill_id: UUID) -> Decimal:
    return Decimal(str(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.bill_id == bill_id, Payment.status == "posted"
    )) or 0))


def _sync_bill_status(db: Session, bill: Bill) -> None:
    paid = _posted_paid(db, bill.id)
    if paid >= bill.total:
        bill.status = "paid"
    elif paid > 0:
        bill.status = "partially_paid"
    else:
        bill.status = "open"


@router.get("/service-catalog", response_model=list[dict], summary="List billable service catalogue")
def list_service_catalog(
    profile: Profile = Depends(require_roles("administrator", "information_officer", "doctor", "nurse", "cashier")),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(select(
        ServiceCatalog.id, ServiceCatalog.code, ServiceCatalog.name,
        ServiceCatalog.category, ServiceCatalog.price, ServiceCatalog.is_active,
    ).where(ServiceCatalog.is_active.is_(True)).order_by(ServiceCatalog.category, ServiceCatalog.name)).mappings().all()
    return [dict(row) for row in rows]



@router.post("/service-catalog", status_code=status.HTTP_201_CREATED, summary="Create a configurable service fee")
def create_service_catalog_item(
    payload: ServiceCatalogCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> dict:
    item = ServiceCatalog(**payload.model_dump())
    db.add(item)
    try:
        db.flush()
        _audit(db, profile, "service_fee.created", "service_catalog", item.id, {
            "code": item.code, "category": item.category, "price": str(item.price),
        })
        db.commit()
        db.refresh(item)
        return {"id": str(item.id), "code": item.code, "name": item.name, "category": item.category, "price": item.price, "is_active": item.is_active}
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Service code already exists.") from exc


@router.patch("/service-catalog/{service_id}", summary="Update a configurable service fee")
def update_service_catalog_item(
    service_id: UUID,
    payload: ServiceCatalogUpdate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> dict:
    item = db.scalar(select(ServiceCatalog).where(ServiceCatalog.id == service_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Service catalog item not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields supplied.")
    for field, value in changes.items():
        setattr(item, field, value)
    _audit(db, profile, "service_fee.updated", "service_catalog", item.id, {
        "fields": sorted(changes.keys()), "price": str(item.price), "is_active": item.is_active,
    })
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "code": item.code, "name": item.name, "category": item.category, "price": item.price, "is_active": item.is_active}


@router.get("/bills", response_model=list[BillRead], summary="List bills")
def list_bills(
    patient_id: UUID | None = None,
    bill_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Bill]:
    roles = set(get_profile_roles(profile.id, db))
    statement = select(Bill)
    if "patient" in roles and not roles.intersection(BILL_READ_ROLES):
        patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if patient_id is None:
            return []
        statement = statement.where(Bill.patient_id == patient_id)
    elif not roles.intersection(BILL_READ_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    elif patient_id:
        statement = statement.where(Bill.patient_id == patient_id)
    if bill_status:
        if bill_status not in {"open", "partially_paid", "paid", "void"}:
            raise HTTPException(status_code=422, detail="Unsupported bill status.")
        statement = statement.where(Bill.status == bill_status)
    return list(db.scalars(statement.order_by(Bill.created_at.desc()).offset(offset).limit(limit)).all())


@router.post("/bills", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: BillCreate,
    profile: Profile = Depends(require_roles(*BILL_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Bill:
    patient = db.scalar(select(Patient).where(Patient.id == payload.patient_id, Patient.is_active.is_(True)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Active patient not found.")
    if payload.encounter_id:
        encounter = db.scalar(select(Encounter).where(Encounter.id == payload.encounter_id))
        if encounter is None or encounter.patient_id != patient.id:
            raise HTTPException(status_code=422, detail="Encounter must belong to the selected patient.")
    for item in payload.items:
        if item.service_id and db.scalar(select(ServiceCatalog.id).where(
            ServiceCatalog.id == item.service_id, ServiceCatalog.is_active.is_(True)
        )) is None:
            raise HTTPException(status_code=422, detail="Every referenced service must be active.")
    subtotal = sum((item.unit_price * item.quantity for item in payload.items), Decimal("0.00"))
    total = subtotal + payload.adjustments
    if total < 0:
        raise HTTPException(status_code=422, detail="Bill total cannot be negative.")
    bill = Bill(
        patient_id=patient.id, encounter_id=payload.encounter_id,
        bill_number=payload.bill_number, status="open",
        subtotal=subtotal, adjustments=payload.adjustments, total=total,
        created_by=profile.id,
    )
    db.add(bill)
    try:
        db.flush()
        for item in payload.items:
            db.add(BillItem(
                bill_id=bill.id, service_id=item.service_id,
                description=item.description, quantity=item.quantity,
                unit_price=item.unit_price, line_total=item.unit_price * item.quantity,
            ))
        _audit(db, profile, "bill.created", "bill", bill.id, {
            "patient_id": str(patient.id), "total": str(total), "item_count": len(payload.items),
        })
        db.commit()
        db.refresh(bill)
        return bill
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bill number already exists or bill data conflicts.") from exc


@router.get("/bills/{bill_id}/items", response_model=list[BillItemRead])
def list_bill_items(
    bill_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[BillItem]:
    roles = set(get_profile_roles(profile.id, db))
    bill = db.scalar(select(Bill).where(Bill.id == bill_id))
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found.")
    if "patient" in roles and not roles.intersection(BILL_READ_ROLES):
        patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if patient_id != bill.patient_id:
            raise HTTPException(status_code=404, detail="Bill not found.")
    elif not roles.intersection(BILL_READ_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return list(db.scalars(select(BillItem).where(BillItem.bill_id == bill_id).order_by(BillItem.id)).all())


@router.get("/bills/{bill_id}/balance", response_model=BillBalanceRead)
def get_bill_balance(
    bill_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> BillBalanceRead:
    roles = set(get_profile_roles(profile.id, db))
    bill = db.scalar(select(Bill).where(Bill.id == bill_id))
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found.")
    if "patient" in roles and not roles.intersection(BILL_READ_ROLES):
        patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if patient_id != bill.patient_id:
            raise HTTPException(status_code=404, detail="Bill not found.")
    elif not roles.intersection(BILL_READ_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    paid = _posted_paid(db, bill.id)
    return BillBalanceRead(
        bill_id=bill.id, bill_number=bill.bill_number, total=bill.total,
        paid=paid, balance=max(Decimal("0.00"), bill.total - paid), status=bill.status,
    )


@router.post("/bills/{bill_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def receive_payment(
    bill_id: UUID,
    payload: PaymentCreate,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=120),
    profile: Profile = Depends(require_roles(*BILL_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Payment:
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(status_code=422, detail="Idempotency-Key cannot be blank.")
    existing_payment = db.scalar(select(Payment).where(Payment.idempotency_key == key))
    if existing_payment:
        if existing_payment.bill_id != bill_id or existing_payment.amount != payload.amount or existing_payment.payment_method != payload.payment_method:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different payment.")
        return existing_payment
    try:
        bill = db.scalar(select(Bill).where(Bill.id == bill_id).with_for_update())
        if bill is None:
            raise HTTPException(status_code=404, detail="Bill not found.")
        if bill.status == "void":
            raise HTTPException(status_code=409, detail="Cannot accept payment for a void bill.")
        paid = _posted_paid(db, bill.id)
        balance = bill.total - paid
        if payload.amount > balance:
            raise HTTPException(status_code=409, detail=f"Payment exceeds the outstanding balance ({balance}).")
        receipt_number = f"RCPT-{uuid4().hex[:12].upper()}"
        payment = Payment(
            bill_id=bill.id, receipt_number=receipt_number, idempotency_key=key,
            amount=payload.amount, payment_method=payload.payment_method,
            status="posted", received_by=profile.id,
        )
        db.add(payment)
        db.flush()
        db.add(Receipt(
            payment_id=payment.id, receipt_number=receipt_number, issued_by=profile.id,
        ))
        remaining = payload.amount
        items = db.scalars(select(BillItem).where(
            BillItem.bill_id == bill.id
        ).order_by(BillItem.id).with_for_update()).all()
        for item in items:
            allocated = Decimal(str(db.scalar(
                select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
                .join(Payment, Payment.id == PaymentAllocation.payment_id)
                .where(
                    PaymentAllocation.bill_item_id == item.id,
                    Payment.status == "posted",
                )
            ) or 0))
            item_balance = max(Decimal("0.00"), item.line_total - allocated)
            allocation = min(remaining, item_balance)
            if allocation > 0:
                db.add(PaymentAllocation(payment_id=payment.id, bill_item_id=item.id, amount=allocation))
                remaining -= allocation
            if remaining == 0:
                break
        _sync_bill_status(db, bill)
        _audit(db, profile, "payment.posted", "payment", payment.id, {
            "bill_id": str(bill.id), "amount": str(payment.amount),
            "receipt_number": receipt_number, "idempotency_key": key,
        })
        notify_roles(db, {"administrator", "information_officer"}, "Payment recorded",
                     "A payment was posted and the bill balance was recalculated.",
                     "billing", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(payment)
        return payment
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        # A concurrent request may have committed the same idempotency key.
        duplicate = db.scalar(select(Payment).where(Payment.idempotency_key == key))
        if duplicate:
            return duplicate
        raise HTTPException(status_code=409, detail="Payment conflicts with current bill state.") from exc


@router.get("/bills/{bill_id}/payments", response_model=list[PaymentRead])
def list_payments(
    bill_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Payment]:
    roles = set(get_profile_roles(profile.id, db))
    bill = db.scalar(select(Bill).where(Bill.id == bill_id))
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found.")
    if "patient" in roles and not roles.intersection(BILL_READ_ROLES):
        patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if patient_id != bill.patient_id:
            raise HTTPException(status_code=404, detail="Bill not found.")
    elif not roles.intersection(BILL_READ_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return list(db.scalars(select(Payment).where(Payment.bill_id == bill_id).order_by(Payment.received_at.desc())).all())


@router.get("/receipts/{receipt_number}", summary="Retrieve a payment receipt")
def get_receipt(
    receipt_number: str,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    roles = set(get_profile_roles(profile.id, db))
    row = db.execute(
        select(Receipt, Payment, Bill)
        .join(Payment, Payment.id == Receipt.payment_id)
        .join(Bill, Bill.id == Payment.bill_id)
        .where(Receipt.receipt_number == receipt_number)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    receipt, payment, bill = row
    if "patient" in roles and not roles.intersection(BILL_READ_ROLES):
        patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if patient_id != bill.patient_id:
            raise HTTPException(status_code=404, detail="Receipt not found.")
    elif not roles.intersection(BILL_READ_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return {
        "receipt_number": receipt.receipt_number,
        "issued_at": receipt.issued_at.isoformat() if receipt.issued_at else None,
        "issued_by": str(receipt.issued_by) if receipt.issued_by else None,
        "payment_id": str(payment.id),
        "payment_amount": payment.amount,
        "payment_method": payment.payment_method,
        "payment_status": payment.status,
        "bill_id": str(bill.id),
        "bill_number": bill.bill_number,
        "patient_id": str(bill.patient_id),
    }


@router.post("/payments/{payment_id}/reverse", response_model=PaymentRead)
def reverse_payment(
    payment_id: UUID,
    payload: PaymentReversal,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> Payment:
    try:
        payment = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found.")
        if payment.status != "posted":
            raise HTTPException(status_code=409, detail="Only posted payments can be reversed.")
        payment.status = "reversed"
        payment.reversed_at = datetime.now(timezone.utc)
        payment.reversal_reason = payload.reason
        bill = db.scalar(select(Bill).where(Bill.id == payment.bill_id).with_for_update())
        if bill:
            _sync_bill_status(db, bill)
        _audit(db, profile, "payment.reversed", "payment", payment.id, {
            "bill_id": str(payment.bill_id), "amount": str(payment.amount),
            "reason": payload.reason,
        })
        notify_roles(db, {"cashier"}, "Payment reversed",
                     "A posted payment was reversed by an administrator; review the updated bill balance.",
                     "billing")
        db.commit()
        db.refresh(payment)
        return payment
    except HTTPException:
        db.rollback()
        raise
