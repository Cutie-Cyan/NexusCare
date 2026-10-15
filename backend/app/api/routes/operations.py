from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.core.notifications import notify_profiles, notify_roles
from app.models import (
    Admission, Appointment, AuditLog, Bed, Bill, Department, DoctorSchedule,
    EmergencyEvent, InventoryItem, InventoryItemTransaction, LaboratoryOrder,
    Notification, OnlineConsultation, Patient, Payment, Profile, ProcurementItem, Ward,
    ProcurementRequest, ReceivingRecord, Supplier, SystemSetting,
)
from app.schemas.operations import (
    AppointmentCreate, AppointmentRead, AppointmentStatusUpdate, DepartmentCreate, DepartmentRead, DepartmentUpdate,
    DoctorScheduleCreate, DoctorScheduleRead, ProcurementItemInput, ProcurementItemRead,
    ProcurementRequestCreate, ProcurementRequestRead, ReceivingRecordCreate, ReceivingRecordRead,
    InventoryItemCreate, InventoryItemRead, InventoryItemTransactionRead,
    InventoryMovementCreate, NotificationCreate, NotificationRead,
    OnlineConsultationCreate, OnlineConsultationRead, OnlineConsultationUpdate, SupplierCreate,
    SupplierRead, SystemSettingRead, SystemSettingWrite,
)

router = APIRouter(tags=["inventory, appointments, and notifications"])
STOCK_ROLES = ("administrator", "pharmacy_staff")
APPOINTMENT_READ_ROLES = {"administrator", "information_officer", "doctor", "nurse"}
APPOINTMENT_CREATE_ROLES = ("administrator", "information_officer", "doctor", "nurse")


def _audit(db: Session, profile: Profile, action: str, kind: str, resource_id: UUID, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id, action=action, resource_type=kind,
        resource_id=str(resource_id), details=details or {},
    ))


def _roles(profile: Profile, db: Session) -> set[str]:
    return set(get_profile_roles(profile.id, db))


def _ensure_appointment_scope(profile: Profile, appointment: Appointment, roles: set[str]) -> None:
    if roles.intersection({"administrator", "information_officer"}):
        return
    if "patient" in roles:
        return  # Patient ownership is checked separately by the calling route.
    if roles.intersection({"doctor", "nurse"}) and (
        appointment.clinician_id == profile.id
        or (profile.department_id is not None and appointment.department_id == profile.department_id)
    ):
        return
    raise HTTPException(status_code=404, detail="Appointment not found in your authorized scope.")


@router.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED, summary="Create a hospital department")
def create_department(
    payload: DepartmentCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> Department:
    department = Department(**payload.model_dump(), is_active=True)
    db.add(department)
    try:
        db.flush()
        _audit(db, profile, "department.created", "department", department.id, {"code": department.code})
        db.commit()
        db.refresh(department)
        return department
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with that code or name already exists.") from exc


@router.get("/departments", summary="List active hospital departments")
def list_departments(
    profile: Profile = Depends(require_roles(
        "administrator", "information_officer", "doctor", "nurse",
        "cashier", "laboratory_staff", "pharmacy_staff",
    )),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.scalars(
        select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
    ).all()
    return [{
        "id": str(row.id), "code": row.code, "name": row.name,
        "description": row.description, "is_active": row.is_active,
    } for row in rows]


@router.patch("/departments/{department_id}", response_model=DepartmentRead, summary="Update or deactivate a department")
def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> Department:
    department = db.scalar(select(Department).where(Department.id == department_id).with_for_update())
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    if changes.get("is_active") is False:
        active_beds = db.scalar(
            select(func.count(Bed.id))
            .join(Ward, Bed.ward_id == Ward.id)
            .where(Ward.department_id == department.id,
                   Ward.is_active.is_(True),
                   Bed.status == "occupied")
        ) or 0
        if active_beds:
            raise HTTPException(status_code=409, detail="Cannot deactivate a department while its wards contain occupied beds.")
    before = {key: getattr(department, key) for key in changes}
    for key, value in changes.items():
        setattr(department, key, value)
    try:
        db.flush()
        _audit(db, profile, "department.updated", "department", department.id, {
            "changed_fields": sorted(changes),
            "before": {key: str(value) if value is not None else None for key, value in before.items()},
            "after": {key: str(value) if value is not None else None for key, value in changes.items()},
        })
        db.commit()
        db.refresh(department)
        return department
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with that code or name already exists.") from exc


@router.get("/suppliers", response_model=list[SupplierRead])
def list_suppliers(
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[Supplier]:
    return list(db.scalars(select(Supplier).where(Supplier.is_active.is_(True)).order_by(Supplier.name)).all())


@router.post("/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> Supplier:
    supplier = Supplier(**payload.model_dump(), is_active=True)
    db.add(supplier)
    try:
        db.flush()
        _audit(db, profile, "supplier.created", "supplier", supplier.id, {"code": supplier.code})
        db.commit()
        db.refresh(supplier)
        return supplier
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Supplier code already exists.") from exc


@router.get("/inventory/items", response_model=list[InventoryItemRead])
def list_inventory_items(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    low_stock_only: bool = False,
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[InventoryItem]:
    statement = select(InventoryItem).where(InventoryItem.is_active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(InventoryItem.name.ilike(term) | InventoryItem.code.ilike(term))
    if low_stock_only:
        statement = statement.where(InventoryItem.quantity_on_hand <= InventoryItem.reorder_level)
    return list(db.scalars(statement.order_by(InventoryItem.name).limit(200)).all())


@router.post("/inventory/items", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> InventoryItem:
    if payload.supplier_id and db.scalar(select(Supplier.id).where(
        Supplier.id == payload.supplier_id, Supplier.is_active.is_(True)
    )) is None:
        raise HTTPException(status_code=422, detail="Active supplier not found.")
    item = InventoryItem(**payload.model_dump(), quantity_on_hand=Decimal("0"), is_active=True)
    db.add(item)
    try:
        db.flush()
        _audit(db, profile, "inventory_item.created", "inventory_item", item.id, {"code": item.code})
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Inventory item code already exists.") from exc


@router.post("/inventory/items/{item_id}/movements", response_model=InventoryItemTransactionRead, status_code=status.HTTP_201_CREATED)
def move_inventory(
    item_id: UUID,
    payload: InventoryMovementCreate,
    profile: Profile = Depends(require_roles(*STOCK_ROLES)),
    db: Session = Depends(get_db),
) -> InventoryItemTransaction:
    try:
        item = db.scalar(select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.is_active.is_(True)
        ).with_for_update())
        if item is None:
            raise HTTPException(status_code=404, detail="Active inventory item not found.")
        if payload.transaction_type == "receipt" and payload.quantity_delta <= 0:
            raise HTTPException(status_code=422, detail="Receipt quantity must be positive.")
        if payload.transaction_type == "issue" and payload.quantity_delta >= 0:
            raise HTTPException(status_code=422, detail="Issue quantity must be negative.")
        updated = item.quantity_on_hand + payload.quantity_delta
        if updated < 0:
            raise HTTPException(status_code=409, detail="Inventory movement would make stock negative.")
        item.quantity_on_hand = updated
        movement = InventoryItemTransaction(
            item_id=item.id, quantity_delta=payload.quantity_delta,
            transaction_type=payload.transaction_type, recorded_by=profile.id,
            notes=payload.notes,
        )
        db.add(movement)
        db.flush()
        _audit(db, profile, "inventory.movement_recorded", "inventory_item_transaction", movement.id, {
            "item_id": str(item.id), "quantity_delta": str(payload.quantity_delta),
            "new_quantity": str(updated),
        })
        if updated <= item.reorder_level:
            notify_roles(db, {"administrator", "pharmacy_staff"}, "Low inventory alert",
                         f"Inventory item {item.code} is at or below its reorder level.",
                         "inventory", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(movement)
        return movement
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Inventory movement conflicts with current stock.") from exc


@router.get("/inventory/items/{item_id}/movements", response_model=list[InventoryItemTransactionRead])
def list_inventory_movements(
    item_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[InventoryItemTransaction]:
    if db.scalar(select(InventoryItem.id).where(InventoryItem.id == item_id)) is None:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    return list(db.scalars(select(InventoryItemTransaction).where(
        InventoryItemTransaction.item_id == item_id
    ).order_by(InventoryItemTransaction.created_at.desc()).limit(limit)).all())



@router.get("/procurement/requests", response_model=list[ProcurementRequestRead])
def list_procurement_requests(
    request_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[ProcurementRequest]:
    statement = select(ProcurementRequest)
    if request_status:
        if request_status not in {"submitted", "approved", "partially_received", "received", "cancelled", "rejected"}:
            raise HTTPException(status_code=422, detail="Unsupported procurement status.")
        statement = statement.where(ProcurementRequest.status == request_status)
    return list(db.scalars(statement.order_by(ProcurementRequest.created_at.desc()).offset(offset).limit(limit)).all())


@router.post("/procurement/requests", response_model=ProcurementRequestRead, status_code=status.HTTP_201_CREATED)
def create_procurement_request(
    payload: ProcurementRequestCreate,
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> ProcurementRequest:
    if payload.supplier_id and db.scalar(select(Supplier.id).where(
        Supplier.id == payload.supplier_id, Supplier.is_active.is_(True)
    )) is None:
        raise HTTPException(status_code=422, detail="Active supplier not found.")
    item_ids = {item.inventory_item_id for item in payload.items}
    active_items = db.scalars(select(InventoryItem.id).where(
        InventoryItem.id.in_(item_ids), InventoryItem.is_active.is_(True)
    )).all()
    if len(active_items) != len(item_ids):
        raise HTTPException(status_code=422, detail="Every requested inventory item must be active.")
    request = ProcurementRequest(
        request_number=payload.request_number, supplier_id=payload.supplier_id,
        requested_by=profile.id, status="submitted", notes=payload.notes,
    )
    db.add(request)
    try:
        db.flush()
        for item in payload.items:
            db.add(ProcurementItem(
                request_id=request.id, inventory_item_id=item.inventory_item_id,
                requested_quantity=item.requested_quantity, received_quantity=Decimal("0"),
                unit_cost=item.unit_cost, notes=item.notes,
            ))
        _audit(db, profile, "procurement_request.submitted", "procurement_request", request.id, {
            "request_number": request.request_number, "item_count": len(payload.items),
        })
        notify_roles(db, {"administrator"}, "Procurement request submitted",
                     "A stock replenishment request is awaiting administrative review.",
                     "procurement", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(request)
        return request
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Procurement request number already exists or request data conflicts.") from exc


@router.get("/procurement/requests/{request_id}/items", response_model=list[ProcurementItemRead])
def list_procurement_items(
    request_id: UUID,
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[ProcurementItem]:
    if db.scalar(select(ProcurementRequest.id).where(ProcurementRequest.id == request_id)) is None:
        raise HTTPException(status_code=404, detail="Procurement request not found.")
    return list(db.scalars(select(ProcurementItem).where(
        ProcurementItem.request_id == request_id
    ).order_by(ProcurementItem.id)).all())


@router.post("/procurement/requests/{request_id}/approve", response_model=ProcurementRequestRead)
def approve_procurement_request(
    request_id: UUID,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> ProcurementRequest:
    request = db.scalar(select(ProcurementRequest).where(
        ProcurementRequest.id == request_id
    ).with_for_update())
    if request is None:
        raise HTTPException(status_code=404, detail="Procurement request not found.")
    if request.status != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted procurement requests can be approved.")
    request.status = "approved"
    request.approved_by = profile.id
    request.approved_at = datetime.now(timezone.utc)
    _audit(db, profile, "procurement_request.approved", "procurement_request", request.id, {
        "request_number": request.request_number,
    })
    notify_roles(db, {"pharmacy_staff"}, "Procurement request approved",
                 "An approved replenishment request is ready for receiving.",
                 "procurement", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(request)
    return request


@router.post("/procurement/requests/{request_id}/items/{item_id}/receive", response_model=ReceivingRecordRead, status_code=status.HTTP_201_CREATED)
def receive_procurement_item(
    request_id: UUID,
    item_id: UUID,
    payload: ReceivingRecordCreate,
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> ReceivingRecord:
    try:
        request = db.scalar(select(ProcurementRequest).where(
            ProcurementRequest.id == request_id
        ).with_for_update())
        if request is None:
            raise HTTPException(status_code=404, detail="Procurement request not found.")
        if request.status not in {"approved", "partially_received"}:
            raise HTTPException(status_code=409, detail="Only approved procurement requests can receive stock.")
        item = db.scalar(select(ProcurementItem).where(
            ProcurementItem.id == item_id, ProcurementItem.request_id == request.id
        ).with_for_update())
        if item is None:
            raise HTTPException(status_code=404, detail="Procurement item not found.")
        remaining = item.requested_quantity - item.received_quantity
        if payload.quantity_received > remaining:
            raise HTTPException(status_code=409, detail=f"Received quantity exceeds remaining ordered quantity ({remaining}).")
        stock_item = db.scalar(select(InventoryItem).where(
            InventoryItem.id == item.inventory_item_id, InventoryItem.is_active.is_(True)
        ).with_for_update())
        if stock_item is None:
            raise HTTPException(status_code=404, detail="Active inventory item not found.")
        stock_item.quantity_on_hand += payload.quantity_received
        item.received_quantity += payload.quantity_received
        receiving = ReceivingRecord(
            procurement_item_id=item.id, quantity_received=payload.quantity_received,
            received_by=profile.id, supplier_reference=payload.supplier_reference,
            notes=payload.notes,
        )
        db.add(receiving)
        db.flush()
        db.add(InventoryItemTransaction(
            item_id=stock_item.id, quantity_delta=payload.quantity_received,
            transaction_type="receipt", reference_id=receiving.id,
            recorded_by=profile.id,
            notes=payload.notes or f"Procurement receipt {request.request_number}",
        ))
        request_items = db.scalars(select(ProcurementItem).where(
            ProcurementItem.request_id == request.id
        )).all()
        request.status = "received" if all(row.received_quantity >= row.requested_quantity for row in request_items) else "partially_received"
        _audit(db, profile, "procurement_item.received", "receiving_record", receiving.id, {
            "request_id": str(request.id), "inventory_item_id": str(stock_item.id),
            "quantity_received": str(payload.quantity_received),
            "new_stock_quantity": str(stock_item.quantity_on_hand),
        })
        notify_roles(db, {"administrator"}, "Inventory receipt recorded",
                     "A procurement delivery was recorded and inventory quantities were updated.",
                     "inventory", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(receiving)
        return receiving
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Receiving record conflicts with current procurement or inventory state.") from exc


@router.get("/whiteboard", summary="View a privacy-conscious operational status board")
def get_whiteboard_summary(
    profile: Profile = Depends(require_roles("administrator", "information_officer", "doctor", "nurse", "laboratory_staff", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "active_admissions": int(db.scalar(select(func.count(Admission.id)).where(Admission.status == "admitted")) or 0),
        "occupied_beds": int(db.scalar(select(func.count(Bed.id)).where(Bed.status == "occupied")) or 0),
        "available_beds": int(db.scalar(select(func.count(Bed.id)).where(Bed.status == "available")) or 0),
        "emergency_queue": int(db.scalar(select(func.count(EmergencyEvent.id)).where(EmergencyEvent.status.in_(["waiting", "in_treatment"]))) or 0),
        "pending_laboratory_orders": int(db.scalar(select(func.count(LaboratoryOrder.id)).where(LaboratoryOrder.status.in_(["ordered", "collected", "in_progress"]))) or 0),
        "low_stock_items": int(db.scalar(select(func.count(InventoryItem.id)).where(InventoryItem.is_active.is_(True), InventoryItem.quantity_on_hand <= InventoryItem.reorder_level)) or 0),
        "active_appointments": int(db.scalar(select(func.count(Appointment.id)).where(Appointment.status.in_(["scheduled", "confirmed", "checked_in"]))) or 0),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/appointments", response_model=list[AppointmentRead])
def list_appointments(
    patient_id: UUID | None = None,
    clinician_id: UUID | None = None,
    appointment_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    roles = _roles(profile, db)
    statement = select(Appointment)
    if "patient" in roles and not roles.intersection(APPOINTMENT_READ_ROLES):
        own_patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if own_patient_id is None:
            return []
        statement = statement.where(Appointment.patient_id == own_patient_id)
    elif roles.intersection(APPOINTMENT_READ_ROLES):
        if patient_id:
            statement = statement.where(Appointment.patient_id == patient_id)
        if clinician_id:
            statement = statement.where(Appointment.clinician_id == clinician_id)
        if not roles.intersection({"administrator", "information_officer"}):
            from sqlalchemy import or_
            scope_conditions = [Appointment.clinician_id == profile.id]
            if profile.department_id is not None:
                scope_conditions.append(Appointment.department_id == profile.department_id)
            statement = statement.where(or_(*scope_conditions))
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    if appointment_status:
        if appointment_status not in {"scheduled", "confirmed", "checked_in", "completed", "cancelled", "no_show"}:
            raise HTTPException(status_code=422, detail="Unsupported appointment status.")
        statement = statement.where(Appointment.status == appointment_status)
    return list(db.scalars(statement.order_by(Appointment.scheduled_at).offset(offset).limit(limit)).all())


@router.post("/appointments", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Appointment:
    if payload.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Appointment must be scheduled in the future.")
    roles = _roles(profile, db)
    if "patient" in roles and not roles.intersection(APPOINTMENT_READ_ROLES):
        own_patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if own_patient_id is None:
            raise HTTPException(status_code=403, detail="Your account is not linked to a patient record.")
        patient_id = own_patient_id
    elif roles.intersection(set(APPOINTMENT_CREATE_ROLES)):
        if payload.patient_id is None:
            raise HTTPException(status_code=422, detail="Staff must select a patient for the appointment.")
        patient_id = payload.patient_id
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    patient = db.scalar(select(Patient).where(Patient.id == patient_id, Patient.is_active.is_(True)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Active patient not found.")
    if payload.department_id and db.scalar(select(Department.id).where(
        Department.id == payload.department_id, Department.is_active.is_(True)
    )) is None:
        raise HTTPException(status_code=422, detail="Active department not found.")
    if (
        roles.intersection({"doctor", "nurse"})
        and not roles.intersection({"administrator", "information_officer"})
        and (profile.department_id is None or payload.department_id != profile.department_id)
    ):
        raise HTTPException(status_code=403, detail="Appointments may only be created for your assigned department.")
    if payload.clinician_id:
        clinician = db.scalar(select(Profile).where(
            Profile.id == payload.clinician_id, Profile.is_active.is_(True)
        ))
        if clinician is None or "doctor" not in _roles(clinician, db):
            raise HTTPException(status_code=422, detail="Clinician must be an active doctor.")
        schedule_rows = db.scalars(select(DoctorSchedule).where(
            DoctorSchedule.doctor_id == payload.clinician_id,
            DoctorSchedule.weekday == payload.scheduled_at.astimezone(ZoneInfo('Asia/Manila')).weekday(),
            DoctorSchedule.is_active.is_(True),
        )).all()
        requested_time = payload.scheduled_at.astimezone(ZoneInfo("Asia/Manila")).strftime("%H:%M")
        if schedule_rows and not any(row.start_time <= requested_time < row.end_time for row in schedule_rows):
            raise HTTPException(status_code=422, detail="Requested time falls outside the clinician schedule.")
        conflict = db.scalar(select(Appointment.id).where(
            Appointment.clinician_id == payload.clinician_id,
            Appointment.scheduled_at == payload.scheduled_at,
            Appointment.status.in_(["scheduled", "confirmed", "checked_in"]),
        ).limit(1))
        if conflict:
            raise HTTPException(status_code=409, detail="Clinician already has an appointment at this exact time.")
    appointment = Appointment(
        patient_id=patient.id, department_id=payload.department_id,
        clinician_id=payload.clinician_id, scheduled_at=payload.scheduled_at,
        reason=payload.reason, created_by=profile.id, status="scheduled",
    )
    db.add(appointment)
    db.flush()
    _audit(db, profile, "appointment.created", "appointment", appointment.id, {
        "patient_id": str(patient.id), "scheduled_at": appointment.scheduled_at.isoformat(),
    })
    notify_roles(db, {"information_officer"}, "Appointment requested",
                 "A new appointment was scheduled or requested.", "appointment", exclude_profile_id=profile.id)
    if appointment.clinician_id:
        notify_profiles(db, {appointment.clinician_id}, "Appointment scheduled",
                        "An appointment has been assigned to your schedule.", "appointment", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentRead)
def update_appointment_status(
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Appointment:
    roles = _roles(profile, db)
    appointment = db.scalar(select(Appointment).where(
        Appointment.id == appointment_id
    ).with_for_update())
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if "patient" in roles and not roles.intersection(APPOINTMENT_READ_ROLES):
        own_patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if own_patient_id != appointment.patient_id:
            raise HTTPException(status_code=404, detail="Appointment not found.")
        if payload.status != "cancelled":
            raise HTTPException(status_code=403, detail="Patients may only cancel their own appointment requests.")
    elif not roles.intersection(set(APPOINTMENT_CREATE_ROLES)):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    _ensure_appointment_scope(profile, appointment, roles)
    if appointment.status in {"completed", "cancelled", "no_show"}:
        raise HTTPException(status_code=409, detail="Closed appointment status cannot be changed.")
    appointment.status = payload.status
    _audit(db, profile, "appointment.status_changed", "appointment", appointment.id, {"status": payload.status})
    notify_roles(db, {"information_officer"}, "Appointment status updated",
                 "An appointment status changed.", "appointment", exclude_profile_id=profile.id)
    if appointment.clinician_id:
        notify_profiles(db, {appointment.clinician_id}, "Appointment status updated",
                        "An appointment on your schedule changed status.", "appointment", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/appointments/{appointment_id}/online-consultation", response_model=OnlineConsultationRead, status_code=status.HTTP_201_CREATED)
def create_online_consultation(
    appointment_id: UUID,
    payload: OnlineConsultationCreate,
    profile: Profile = Depends(require_roles("administrator", "doctor")),
    db: Session = Depends(get_db),
) -> OnlineConsultation:
    appointment = db.scalar(select(Appointment).where(Appointment.id == appointment_id))
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    roles = _roles(profile, db)
    _ensure_appointment_scope(profile, appointment, roles)
    if "doctor" in roles and "administrator" not in roles and appointment.clinician_id != profile.id:
        raise HTTPException(status_code=403, detail="Only the assigned clinician may create this online consultation.")
    if appointment.status in {"cancelled", "completed", "no_show"}:
        raise HTTPException(status_code=409, detail="Appointment is not eligible for an online consultation.")
    existing = db.scalar(select(OnlineConsultation).where(OnlineConsultation.appointment_id == appointment.id))
    if existing:
        raise HTTPException(status_code=409, detail="Online consultation already exists for this appointment.")
    consultation = OnlineConsultation(
        appointment_id=appointment.id, meeting_url=payload.meeting_url, status="scheduled",
    )
    db.add(consultation)
    db.flush()
    _audit(db, profile, "online_consultation.created", "online_consultation", consultation.id, {
        "appointment_id": str(appointment.id),
    })
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/online-consultations", response_model=list[OnlineConsultationRead])
def list_online_consultations(
    consultation_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[OnlineConsultation]:
    roles = _roles(profile, db)
    statement = select(OnlineConsultation).join(
        Appointment, Appointment.id == OnlineConsultation.appointment_id
    )
    if "patient" in roles and not roles.intersection(APPOINTMENT_READ_ROLES):
        own_patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if own_patient_id is None:
            return []
        statement = statement.where(Appointment.patient_id == own_patient_id)
    elif not roles.intersection(APPOINTMENT_READ_ROLES | {"patient"}):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    elif not roles.intersection({"administrator", "information_officer"}):
        from sqlalchemy import or_
        scope_conditions = [Appointment.clinician_id == profile.id]
        if profile.department_id is not None:
            scope_conditions.append(Appointment.department_id == profile.department_id)
        statement = statement.where(or_(*scope_conditions))
    if consultation_status:
        if consultation_status not in {"requested", "scheduled", "in_progress", "completed", "cancelled"}:
            raise HTTPException(status_code=422, detail="Unsupported online consultation status.")
        statement = statement.where(OnlineConsultation.status == consultation_status)
    return list(db.scalars(statement.order_by(OnlineConsultation.id.desc()).offset(offset).limit(limit)).all())


@router.post("/appointments/{appointment_id}/request-online-consultation", response_model=OnlineConsultationRead, status_code=status.HTTP_201_CREATED)
def request_online_consultation(
    appointment_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> OnlineConsultation:
    roles = _roles(profile, db)
    appointment = db.scalar(select(Appointment).where(Appointment.id == appointment_id))
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if "patient" in roles and not roles.intersection(APPOINTMENT_READ_ROLES):
        own_patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if own_patient_id != appointment.patient_id:
            raise HTTPException(status_code=404, detail="Appointment not found.")
    elif not roles.intersection(set(APPOINTMENT_CREATE_ROLES)):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    else:
        _ensure_appointment_scope(profile, appointment, roles)
    if appointment.status not in {"scheduled", "confirmed"}:
        raise HTTPException(status_code=409, detail="Only scheduled or confirmed appointments can request an online consultation.")
    if db.scalar(select(OnlineConsultation.id).where(OnlineConsultation.appointment_id == appointment.id)):
        raise HTTPException(status_code=409, detail="An online consultation record already exists.")
    consultation = OnlineConsultation(appointment_id=appointment.id, status="requested")
    db.add(consultation)
    db.flush()
    _audit(db, profile, "online_consultation.requested", "online_consultation", consultation.id, {
        "appointment_id": str(appointment.id),
    })
    notify_roles(db, {"administrator", "doctor"}, "Online consultation requested",
                 "An appointment has an online consultation request awaiting review.", "appointment", exclude_profile_id=profile.id)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.patch("/online-consultations/{consultation_id}", response_model=OnlineConsultationRead)
def update_online_consultation(
    consultation_id: UUID,
    payload: OnlineConsultationUpdate,
    profile: Profile = Depends(require_roles("administrator", "doctor")),
    db: Session = Depends(get_db),
) -> OnlineConsultation:
    consultation = db.scalar(select(OnlineConsultation).where(
        OnlineConsultation.id == consultation_id
    ).with_for_update())
    if consultation is None:
        raise HTTPException(status_code=404, detail="Online consultation not found.")
    appointment = db.scalar(select(Appointment).where(Appointment.id == consultation.appointment_id))
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    roles = _roles(profile, db)
    _ensure_appointment_scope(profile, appointment, roles)
    if "doctor" in roles and "administrator" not in roles and appointment.clinician_id != profile.id:
        raise HTTPException(status_code=403, detail="Only the assigned clinician may update this online consultation.")
    if consultation.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Closed online consultations cannot be changed.")
    if payload.status == "in_progress" and consultation.status not in {"requested", "scheduled"}:
        raise HTTPException(status_code=409, detail="Only requested or scheduled sessions can start.")
    if payload.status == "completed" and consultation.status != "in_progress":
        raise HTTPException(status_code=409, detail="Only an active session can be completed.")
    consultation.status = payload.status
    if payload.meeting_url is not None:
        consultation.meeting_url = payload.meeting_url.strip() or None
    if payload.status == "in_progress":
        consultation.started_at = datetime.now(timezone.utc)
    if payload.status in {"completed", "cancelled"}:
        consultation.ended_at = datetime.now(timezone.utc)
    _audit(db, profile, "online_consultation.updated", "online_consultation", consultation.id, {
        "status": consultation.status, "appointment_id": str(consultation.appointment_id),
    })
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Notification]:
    statement = select(Notification).where(Notification.recipient_profile_id == profile.id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    return list(db.scalars(statement.order_by(Notification.created_at.desc()).limit(limit)).all())


@router.post("/notifications", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> Notification:
    recipient = db.scalar(select(Profile).where(
        Profile.id == payload.recipient_profile_id, Profile.is_active.is_(True)
    ))
    if recipient is None:
        raise HTTPException(status_code=404, detail="Active recipient profile not found.")
    notification = Notification(**payload.model_dump())
    db.add(notification)
    db.flush()
    _audit(db, profile, "notification.created", "notification", notification.id, {
        "recipient_profile_id": str(recipient.id), "category": notification.category,
    })
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.scalar(select(Notification).where(
        Notification.id == notification_id,
        Notification.recipient_profile_id == profile.id,
    ).with_for_update())
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return notification


@router.post("/doctor-schedules", response_model=DoctorScheduleRead, status_code=status.HTTP_201_CREATED)
def create_doctor_schedule(
    payload: DoctorScheduleCreate,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> DoctorSchedule:
    doctor = db.scalar(select(Profile).where(Profile.id == payload.doctor_id, Profile.is_active.is_(True)))
    if doctor is None or "doctor" not in _roles(doctor, db):
        raise HTTPException(status_code=422, detail="Schedule owner must be an active doctor profile.")
    if payload.department_id and db.scalar(select(Department.id).where(
        Department.id == payload.department_id, Department.is_active.is_(True)
    )) is None:
        raise HTTPException(status_code=422, detail="Active department not found.")
    overlap = db.scalar(select(DoctorSchedule.id).where(
        DoctorSchedule.doctor_id == payload.doctor_id,
        DoctorSchedule.weekday == payload.weekday,
        DoctorSchedule.is_active.is_(True),
        DoctorSchedule.start_time < payload.end_time,
        DoctorSchedule.end_time > payload.start_time,
    ).limit(1))
    if overlap:
        raise HTTPException(status_code=409, detail="Doctor schedule overlaps an existing active schedule.")
    schedule = DoctorSchedule(**payload.model_dump())
    db.add(schedule)
    db.flush()
    _audit(db, profile, "doctor_schedule.created", "doctor_schedule", schedule.id, {
        "doctor_id": str(schedule.doctor_id), "weekday": schedule.weekday,
        "start_time": schedule.start_time, "end_time": schedule.end_time,
    })
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/doctor-schedules")
def list_doctor_schedules(
    doctor_id: UUID | None = None,
    profile: Profile = Depends(require_roles("administrator", "information_officer", "doctor")),
    db: Session = Depends(get_db),
) -> list[dict]:
    statement = select(DoctorSchedule)
    if doctor_id:
        statement = statement.where(DoctorSchedule.doctor_id == doctor_id)
    elif "doctor" in _roles(profile, db) and "administrator" not in _roles(profile, db):
        statement = statement.where(DoctorSchedule.doctor_id == profile.id)
    rows = db.scalars(statement.order_by(DoctorSchedule.doctor_id, DoctorSchedule.weekday, DoctorSchedule.start_time)).all()
    return [{
        "id": row.id, "doctor_id": row.doctor_id, "department_id": row.department_id,
        "weekday": row.weekday, "start_time": row.start_time, "end_time": row.end_time,
        "is_active": row.is_active,
    } for row in rows]


@router.put("/system-settings/{setting_key}", response_model=SystemSettingRead)
def upsert_system_setting(
    setting_key: str,
    payload: SystemSettingWrite,
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> SystemSetting:
    key = setting_key.strip()
    if not key or len(key) > 120:
        raise HTTPException(status_code=422, detail="Setting key must be 1–120 characters.")
    setting = db.scalar(select(SystemSetting).where(
        SystemSetting.setting_key == key
    ).with_for_update())
    if setting is None:
        setting = SystemSetting(
            setting_key=key, setting_value=payload.setting_value,
            description=payload.description, updated_by=profile.id,
        )
        db.add(setting)
    else:
        setting.setting_value = payload.setting_value
        setting.description = payload.description
        setting.updated_by = profile.id
    db.flush()
    _audit(db, profile, "system_setting.updated", "system_setting", setting.id, {"setting_key": key})
    db.commit()
    db.refresh(setting)
    return setting


@router.get("/system-settings")
def list_system_settings(
    profile: Profile = Depends(require_roles("administrator")),
    db: Session = Depends(get_db),
) -> list[SystemSettingRead]:
    return list(db.scalars(select(SystemSetting).order_by(SystemSetting.setting_key)).all())


@router.get("/reports/summary")
def reports_summary(
    profile: Profile = Depends(require_roles("administrator", "information_officer", "cashier")),
    db: Session = Depends(get_db),
) -> dict:
    patient_count = int(db.scalar(select(func.count(Patient.id)).where(Patient.is_active.is_(True))) or 0)
    active_admissions = int(db.scalar(select(func.count(Admission.id)).where(Admission.status == "admitted")) or 0)
    appointment_count = int(db.scalar(select(func.count(Appointment.id)).where(
        Appointment.status.in_(["scheduled", "confirmed", "checked_in"])
    )) or 0)
    posted_revenue = Decimal(str(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.status == "posted"
    )) or 0))
    open_bills = int(db.scalar(select(func.count(Bill.id)).where(
        Bill.status.in_(["open", "partially_paid"])
    )) or 0)
    low_stock_count = int(db.scalar(select(func.count(InventoryItem.id)).where(
        InventoryItem.is_active.is_(True), InventoryItem.quantity_on_hand <= InventoryItem.reorder_level
    )) or 0)
    return {
        "active_patients": patient_count,
        "active_admissions": active_admissions,
        "upcoming_or_active_appointments": appointment_count,
        "posted_payments_total": posted_revenue,
        "open_bills": open_bills,
        "low_stock_items": low_stock_count,
    }
