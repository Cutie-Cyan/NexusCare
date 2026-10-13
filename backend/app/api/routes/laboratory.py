from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, require_roles
from app.db.session import get_db
from app.core.billing import add_service_charge
from app.core.notifications import notify_roles
from app.models import (
    AuditLog, BillItem, Encounter, LaboratoryOrder, LaboratoryResult, LaboratoryTest,
    Payment, PaymentAllocation, Profile,
)
from app.schemas.laboratory import (
    LaboratoryBillingAuthorizationCreate, LaboratoryOrderCreate, LaboratoryOrderRead,
    LaboratoryOrderStatusUpdate, LaboratoryResultCreate, LaboratoryResultRead,
    LaboratoryTestCreate, LaboratoryTestRead,
)

router = APIRouter(tags=["laboratory"])


def _audit(
    db: Session,
    profile: Profile,
    action: str,
    resource_type: str,
    resource_id: UUID,
    details: dict | None = None,
) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
    ))


@router.get(
    "/laboratory-tests",
    response_model=list[LaboratoryTestRead],
    summary="List active laboratory tests",
)
def list_laboratory_tests(
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(require_roles(
        "administrator", "doctor", "nurse", "laboratory_staff",
    )),
    db: Session = Depends(get_db),
) -> list[LaboratoryTest]:
    statement = select(LaboratoryTest)
    if not include_inactive:
        statement = statement.where(LaboratoryTest.is_active.is_(True))
    return list(db.scalars(
        statement.order_by(LaboratoryTest.name).offset(offset).limit(limit)
    ).all())


@router.post(
    "/laboratory-tests",
    response_model=LaboratoryTestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a laboratory test catalog item",
)
def create_laboratory_test(
    payload: LaboratoryTestCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> LaboratoryTest:
    test = LaboratoryTest(**payload.model_dump())
    db.add(test)
    try:
        db.flush()
        _audit(db, profile, "laboratory_test.created", "laboratory_test", test.id)
        db.commit()
        db.refresh(test)
        return test
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A laboratory test with this code already exists.") from exc


@router.get(
    "/laboratory-orders",
    response_model=list[LaboratoryOrderRead],
    summary="List laboratory orders",
)
def list_laboratory_orders(
    order_status: str | None = Query(default=None, alias="status", max_length=30),
    encounter_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(require_roles(
        "administrator", "doctor", "nurse", "laboratory_staff",
    )),
    db: Session = Depends(get_db),
) -> list[LaboratoryOrder]:
    allowed_statuses = {"ordered", "collected", "in_progress", "completed", "cancelled"}
    if order_status and order_status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Unsupported laboratory order status.")
    statement = select(LaboratoryOrder)
    if order_status:
        statement = statement.where(LaboratoryOrder.status == order_status)
    if encounter_id:
        statement = statement.where(LaboratoryOrder.encounter_id == encounter_id)
    return list(db.scalars(
        statement.order_by(LaboratoryOrder.ordered_at.desc()).offset(offset).limit(limit)
    ).all())


@router.post(
    "/laboratory-orders",
    response_model=LaboratoryOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Order a laboratory test for an encounter",
)
def create_laboratory_order(
    payload: LaboratoryOrderCreate,
    profile: Profile = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
) -> LaboratoryOrder:
    encounter = db.scalar(select(Encounter).where(
        Encounter.id == payload.encounter_id
    ).with_for_update())
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot order tests for a closed encounter.")
    lab_test = db.scalar(select(LaboratoryTest).where(
        LaboratoryTest.id == payload.test_id,
        LaboratoryTest.is_active.is_(True),
    ))
    if lab_test is None:
        raise HTTPException(status_code=404, detail="Active laboratory test not found.")

    order = LaboratoryOrder(
        encounter_id=encounter.id,
        test_id=lab_test.id,
        ordered_by=profile.id,
        priority=payload.priority,
        clinical_notes=payload.clinical_notes,
        status="ordered",
    )
    db.add(order)
    db.flush()
    _audit(db, profile, "laboratory_order.created", "laboratory_order", order.id, {
        "encounter_id": str(encounter.id),
        "test_id": str(lab_test.id),
        "priority": order.priority,
    })
    if lab_test.base_fee > 0:
        add_service_charge(
            db, encounter.patient_id, encounter.id,
            f"Lab order {order.id}: {lab_test.name}", lab_test.base_fee,
        )
    notify_roles(db, {"laboratory_staff"}, "New laboratory request",
                 "A laboratory request is ready for eligibility review.", "laboratory")
    notify_roles(db, {"cashier"}, "Laboratory charge added",
                 "A laboratory request added a charge to the encounter bill.", "billing")
    db.commit()
    db.refresh(order)
    return order


@router.patch(
    "/laboratory-orders/{order_id}/status",
    response_model=LaboratoryOrderRead,
    summary="Update laboratory processing status",
)
def update_laboratory_order_status(
    order_id: UUID,
    payload: LaboratoryOrderStatusUpdate,
    profile: Profile = Depends(require_roles("laboratory_staff")),
    db: Session = Depends(get_db),
) -> LaboratoryOrder:
    order = db.scalar(select(LaboratoryOrder).where(
        LaboratoryOrder.id == order_id
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Laboratory order not found.")
    if order.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="This laboratory order is already closed.")
    if payload.status == "collected" and order.status != "ordered":
        raise HTTPException(status_code=409, detail="Only ordered tests can be marked collected.")
    if payload.status in {"collected", "in_progress", "completed"}:
        lab_test = db.scalar(select(LaboratoryTest).where(LaboratoryTest.id == order.test_id))
        if lab_test and lab_test.base_fee > 0:
            charge_description = f"Lab order {order.id}: {lab_test.name}"
            charge_item = db.scalar(select(BillItem).where(BillItem.description == charge_description))
            paid_for_charge = Decimal("0.00")
            if charge_item is not None:
                paid_for_charge = Decimal(str(db.scalar(
                    select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
                    .join(Payment, Payment.id == PaymentAllocation.payment_id)
                    .where(PaymentAllocation.bill_item_id == charge_item.id, Payment.status == "posted")
                ) or 0))
            authorized = db.scalar(select(AuditLog.id).where(
                AuditLog.action == "laboratory_billing.authorized",
                AuditLog.resource_id == str(order.id),
            ))
            if (charge_item is None or paid_for_charge < charge_item.line_total) and authorized is None:
                raise HTTPException(status_code=409, detail="Laboratory processing requires payment for this test or an authorized billing arrangement.")
    if payload.status == "in_progress" and order.status not in {"ordered", "collected"}:
        raise HTTPException(status_code=409, detail="Only ordered or collected tests can be started.")
    if payload.status == "completed":
        verified_result = db.scalar(select(LaboratoryResult.id).where(
            LaboratoryResult.order_id == order.id, LaboratoryResult.status == "verified"
        ))
        if verified_result is None:
            raise HTTPException(status_code=409, detail="A laboratory order can only be completed after an independent result verification.")
    if payload.status == "cancelled":
        existing_result = db.scalar(select(LaboratoryResult.id).where(
            LaboratoryResult.order_id == order.id
        ))
        if existing_result is not None:
            raise HTTPException(status_code=409, detail="Orders with results cannot be cancelled.")
    old_status = order.status
    order.status = payload.status
    _audit(db, profile, "laboratory_order.status_updated", "laboratory_order", order.id, {
        "previous_status": old_status, "status": order.status,
    })
    db.commit()
    db.refresh(order)
    return order


@router.post("/laboratory-orders/{order_id}/billing-authorization", summary="Authorize a laboratory billing arrangement")
def authorize_laboratory_billing(
    order_id: UUID,
    payload: LaboratoryBillingAuthorizationCreate,
    profile: Profile = Depends(require_roles("administrator", "cashier")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    order = db.scalar(select(LaboratoryOrder).where(LaboratoryOrder.id == order_id))
    if order is None:
        raise HTTPException(status_code=404, detail="Laboratory order not found.")
    if order.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Closed laboratory orders cannot receive a billing authorization.")
    existing = db.scalar(select(AuditLog.id).where(
        AuditLog.action == "laboratory_billing.authorized", AuditLog.resource_id == str(order.id)
    ))
    if existing:
        raise HTTPException(status_code=409, detail="A billing arrangement is already authorized for this order.")
    _audit(db, profile, "laboratory_billing.authorized", "laboratory_order", order.id, {
        "reason": payload.reason, "authorized_by": str(profile.id),
    })
    notify_roles(db, {"laboratory_staff"}, "Laboratory billing authorized",
                 "An authorized billing arrangement is recorded for a laboratory request.", "billing")
    db.commit()
    return {"status": "authorized", "order_id": str(order.id)}


@router.get(
    "/laboratory-orders/{order_id}/result",
    response_model=LaboratoryResultRead,
    summary="Get a laboratory result",
)
def get_laboratory_result(
    order_id: UUID,
    profile: Profile = Depends(require_roles(
        "administrator", "doctor", "nurse", "laboratory_staff",
    )),
    db: Session = Depends(get_db),
) -> LaboratoryResult:
    result = db.scalar(select(LaboratoryResult).where(
        LaboratoryResult.order_id == order_id
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Laboratory result not found.")
    return result


@router.post(
    "/laboratory-orders/{order_id}/result",
    response_model=LaboratoryResultRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enter a laboratory result",
)
def create_laboratory_result(
    order_id: UUID,
    payload: LaboratoryResultCreate,
    profile: Profile = Depends(require_roles("laboratory_staff")),
    db: Session = Depends(get_db),
) -> LaboratoryResult:
    order = db.scalar(select(LaboratoryOrder).where(
        LaboratoryOrder.id == order_id
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Laboratory order not found.")
    if order.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot add a result to a closed order.")
    existing = db.scalar(select(LaboratoryResult.id).where(
        LaboratoryResult.order_id == order.id
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="A result already exists for this order.")
    result = LaboratoryResult(
        order_id=order.id,
        result_text=payload.result_text,
        result_data=payload.result_data,
        entered_by=profile.id,
        status="draft",
    )
    db.add(result)
    order.status = "in_progress"
    db.flush()
    _audit(db, profile, "laboratory_result.created", "laboratory_result", result.id, {
        "order_id": str(order.id),
    })
    db.commit()
    db.refresh(result)
    return result


@router.post(
    "/laboratory-orders/{order_id}/verify-result",
    response_model=LaboratoryResultRead,
    summary="Verify and release a laboratory result",
)
def verify_laboratory_result(
    order_id: UUID,
    profile: Profile = Depends(require_roles("laboratory_staff")),
    db: Session = Depends(get_db),
) -> LaboratoryResult:
    order = db.scalar(select(LaboratoryOrder).where(
        LaboratoryOrder.id == order_id
    ).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Laboratory order not found.")
    result = db.scalar(select(LaboratoryResult).where(
        LaboratoryResult.order_id == order.id
    ).with_for_update())
    if result is None:
        raise HTTPException(status_code=404, detail="Laboratory result not found.")
    if result.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft results can be verified.")
    if result.entered_by == profile.id:
        raise HTTPException(status_code=409, detail="A different laboratory staff member must verify this result.")
    result.verified_by = profile.id
    result.status = "verified"
    result.released_at = datetime.now(timezone.utc)
    order.status = "completed"
    _audit(db, profile, "laboratory_result.verified", "laboratory_result", result.id, {
        "order_id": str(order.id),
    })
    notify_roles(db, {"doctor", "nurse"}, "Laboratory result released",
                 "A laboratory result was verified and is available to authorized clinical staff.",
                 "laboratory", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(result)
    return result
