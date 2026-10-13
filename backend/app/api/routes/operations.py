from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.models import (
    Appointment, AuditLog, Department, DoctorSchedule, InventoryItem,
    InventoryItemTransaction, Notification, OnlineConsultation, Patient,
    Profile, Supplier, SystemSetting,
)
from app.schemas.operations import (
    AppointmentCreate, AppointmentRead, AppointmentStatusUpdate,
    InventoryItemCreate, InventoryItemRead, InventoryItemTransactionRead,
    InventoryMovementCreate, NotificationCreate, NotificationRead,
    OnlineConsultationCreate, OnlineConsultationRead, SupplierCreate,
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
    profile: Profile = Depends(require_roles(*APPOINTMENT_CREATE_ROLES)),
    db: Session = Depends(get_db),
) -> Appointment:
    if payload.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Appointment must be scheduled in the future.")
    patient = db.scalar(select(Patient).where(Patient.id == payload.patient_id, Patient.is_active.is_(True)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Active patient not found.")
    if payload.department_id and db.scalar(select(Department.id).where(
        Department.id == payload.department_id, Department.is_active.is_(True)
    )) is None:
        raise HTTPException(status_code=422, detail="Active department not found.")
    if payload.clinician_id:
        clinician = db.scalar(select(Profile).where(
            Profile.id == payload.clinician_id, Profile.is_active.is_(True)
        ))
        if clinician is None or "doctor" not in _roles(clinician, db):
            raise HTTPException(status_code=422, detail="Clinician must be an active doctor.")
        conflict = db.scalar(select(Appointment.id).where(
            Appointment.clinician_id == payload.clinician_id,
            Appointment.scheduled_at == payload.scheduled_at,
            Appointment.status.in_(["scheduled", "confirmed", "checked_in"]),
        ).limit(1))
        if conflict:
            raise HTTPException(status_code=409, detail="Clinician already has an appointment at this exact time.")
    appointment = Appointment(**payload.model_dump(), created_by=profile.id, status="scheduled")
    db.add(appointment)
    db.flush()
    _audit(db, profile, "appointment.created", "appointment", appointment.id, {
        "patient_id": str(patient.id), "scheduled_at": appointment.scheduled_at.isoformat(),
    })
    db.commit()
    db.refresh(appointment)
    return appointment


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentRead)
def update_appointment_status(
    appointment_id: UUID,
    payload: AppointmentStatusUpdate,
    profile: Profile = Depends(require_roles("administrator", "information_officer", "doctor", "nurse")),
    db: Session = Depends(get_db),
) -> Appointment:
    appointment = db.scalar(select(Appointment).where(
        Appointment.id == appointment_id
    ).with_for_update())
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if appointment.status in {"completed", "cancelled", "no_show"}:
        raise HTTPException(status_code=409, detail="Closed appointment status cannot be changed.")
    appointment.status = payload.status
    _audit(db, profile, "appointment.status_changed", "appointment", appointment.id, {"status": payload.status})
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
    active_admissions = int(db.scalar(select(func.count()).select_from(__import__("app.models", fromlist=["Admission"]).Admission).where(
        __import__("app.models", fromlist=["Admission"]).Admission.status == "admitted"
    )) or 0)
    appointment_count = int(db.scalar(select(func.count(Appointment.id)).where(
        Appointment.status.in_(["scheduled", "confirmed", "checked_in"])
    )) or 0)
    posted_revenue = Decimal(str(db.scalar(select(func.coalesce(func.sum(__import__("app.models", fromlist=["Payment"]).Payment.amount), 0)).where(
        __import__("app.models", fromlist=["Payment"]).Payment.status == "posted"
    )) or 0))
    open_bills = int(db.scalar(select(func.count()).select_from(__import__("app.models", fromlist=["Bill"]).Bill).where(
        __import__("app.models", fromlist=["Bill"]).Bill.status.in_(["open", "partially_paid"])
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
