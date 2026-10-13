from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.core.billing import add_service_charge
from app.core.notifications import notify_roles
from app.models import (
    AuditLog, Encounter, InventoryTransaction, Medicine, MedicineBatch,
    PharmacyDispensing, Prescription, PrescriptionItem, Profile,
)
from app.schemas.pharmacy import (
    DispenseCreate, DispensingRead, InventoryStockRead, MedicineBatchCreate,
    MedicineBatchRead, MedicineCreate, MedicineRead, PrescriptionCreate,
    PrescriptionItemRead, PrescriptionRead,
)

router = APIRouter(tags=["pharmacy"])
PHARMACY_STAFF = ("pharmacy_staff",)
STOCK_MANAGERS = ("administrator", "pharmacy_staff")


def _audit(db: Session, profile: Profile, action: str, kind: str, resource_id: UUID, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id, action=action, resource_type=kind,
        resource_id=str(resource_id), details=details or {},
    ))


@router.get("/medicines", response_model=list[MedicineRead], summary="List medicine catalogue")
def list_medicines(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    active_only: bool = True,
    profile: Profile = Depends(require_roles("administrator", "doctor", "nurse", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[Medicine]:
    statement = select(Medicine)
    if active_only:
        statement = statement.where(Medicine.is_active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(Medicine.name.ilike(term) | Medicine.code.ilike(term))
    return list(db.scalars(statement.order_by(Medicine.name).limit(100)).all())


@router.post("/medicines", response_model=MedicineRead, status_code=status.HTTP_201_CREATED)
def create_medicine(
    payload: MedicineCreate,
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> Medicine:
    medicine = Medicine(**payload.model_dump(), is_active=True)
    db.add(medicine)
    try:
        db.flush()
        _audit(db, profile, "medicine.created", "medicine", medicine.id, {"code": medicine.code})
        db.commit()
        db.refresh(medicine)
        return medicine
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Medicine code already exists.") from exc


@router.get("/medicine-batches", response_model=list[MedicineBatchRead])
def list_medicine_batches(
    medicine_id: UUID | None = None,
    available_only: bool = True,
    profile: Profile = Depends(require_roles("administrator", "doctor", "nurse", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[MedicineBatch]:
    statement = select(MedicineBatch)
    if medicine_id:
        statement = statement.where(MedicineBatch.medicine_id == medicine_id)
    if available_only:
        statement = statement.where(
            MedicineBatch.quantity_on_hand > 0,
            (MedicineBatch.expires_on.is_(None)) | (MedicineBatch.expires_on >= date.today()),
        )
    return list(db.scalars(statement.order_by(MedicineBatch.expires_on.asc().nullslast())).all())


@router.post("/medicine-batches", response_model=MedicineBatchRead, status_code=status.HTTP_201_CREATED)
def receive_medicine_batch(
    payload: MedicineBatchCreate,
    profile: Profile = Depends(require_roles(*STOCK_MANAGERS)),
    db: Session = Depends(get_db),
) -> MedicineBatch:
    if payload.expires_on and payload.expires_on < date.today():
        raise HTTPException(status_code=422, detail="Cannot receive a batch that is already expired.")
    medicine = db.scalar(select(Medicine).where(
        Medicine.id == payload.medicine_id, Medicine.is_active.is_(True)
    ))
    if medicine is None:
        raise HTTPException(status_code=404, detail="Active medicine not found.")
    batch = MedicineBatch(
        medicine_id=medicine.id, batch_number=payload.batch_number,
        quantity_on_hand=payload.quantity, unit_cost=payload.unit_cost,
        selling_price=payload.selling_price, expires_on=payload.expires_on,
    )
    db.add(batch)
    try:
        db.flush()
        db.add(InventoryTransaction(
            medicine_batch_id=batch.id, quantity_delta=payload.quantity,
            transaction_type="receipt", recorded_by=profile.id,
            notes="Initial batch receipt",
        ))
        _audit(db, profile, "medicine_batch.received", "medicine_batch", batch.id, {
            "medicine_id": str(medicine.id), "quantity": payload.quantity,
        })
        db.commit()
        db.refresh(batch)
        return batch
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Batch number already exists for this medicine.") from exc


@router.get("/pharmacy/stock", response_model=list[InventoryStockRead], summary="View current medicine stock")
def pharmacy_stock(
    profile: Profile = Depends(require_roles("administrator", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[InventoryStockRead]:
    medicines = db.scalars(select(Medicine).where(Medicine.is_active.is_(True)).order_by(Medicine.name)).all()
    output = []
    for medicine in medicines:
        batches = list(db.scalars(select(MedicineBatch).where(
            MedicineBatch.medicine_id == medicine.id
        ).order_by(MedicineBatch.expires_on.asc().nullslast())).all())
        total = sum(
            batch.quantity_on_hand for batch in batches
            if batch.expires_on is None or batch.expires_on >= date.today()
        )
        stock_status = "out_of_stock" if total == 0 else "low_stock" if total <= medicine.reorder_level else "in_stock"
        output.append(InventoryStockRead(
            medicine_id=medicine.id, medicine_name=medicine.name,
            reorder_level=medicine.reorder_level, total_quantity=total,
            batches=batches, stock_status=stock_status,
        ))
    return output


@router.post("/prescriptions", response_model=PrescriptionRead, status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreate,
    profile: Profile = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
) -> Prescription:
    encounter = db.scalar(select(Encounter).where(
        Encounter.id == payload.encounter_id
    ).with_for_update())
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot prescribe for a closed encounter.")
    medicine_ids = {item.medicine_id for item in payload.items}
    medicines = db.scalars(select(Medicine).where(
        Medicine.id.in_(medicine_ids), Medicine.is_active.is_(True)
    )).all()
    if len(medicines) != len(medicine_ids):
        raise HTTPException(status_code=422, detail="Every prescribed medicine must be active.")
    prescription = Prescription(
        encounter_id=encounter.id, prescribed_by=profile.id,
        status="issued", instructions=payload.instructions,
    )
    db.add(prescription)
    db.flush()
    for item in payload.items:
        db.add(PrescriptionItem(prescription_id=prescription.id, **item.model_dump()))
    _audit(db, profile, "prescription.issued", "prescription", prescription.id, {
        "encounter_id": str(encounter.id), "item_count": len(payload.items),
    })
    notify_roles(db, {"pharmacy_staff"}, "New prescription",
                 "A doctor issued a prescription that is ready for pharmacy review.", "pharmacy")
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("/prescriptions", response_model=list[PrescriptionRead])
def list_prescriptions(
    prescription_status: str | None = Query(default=None, alias="status", max_length=30),
    encounter_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(require_roles("administrator", "doctor", "nurse", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[Prescription]:
    statement = select(Prescription)
    if prescription_status:
        if prescription_status not in {"issued", "partially_dispensed", "dispensed", "cancelled"}:
            raise HTTPException(status_code=422, detail="Unsupported prescription status.")
        statement = statement.where(Prescription.status == prescription_status)
    if encounter_id:
        statement = statement.where(Prescription.encounter_id == encounter_id)
    return list(db.scalars(statement.order_by(Prescription.created_at.desc()).offset(offset).limit(limit)).all())


@router.get("/prescriptions/{prescription_id}/items", response_model=list[PrescriptionItemRead])
def list_prescription_items(
    prescription_id: UUID,
    profile: Profile = Depends(require_roles("administrator", "doctor", "nurse", "pharmacy_staff")),
    db: Session = Depends(get_db),
) -> list[PrescriptionItem]:
    if db.scalar(select(Prescription.id).where(Prescription.id == prescription_id)) is None:
        raise HTTPException(status_code=404, detail="Prescription not found.")
    return list(db.scalars(select(PrescriptionItem).where(
        PrescriptionItem.prescription_id == prescription_id
    ).order_by(PrescriptionItem.id)).all())


@router.post("/prescription-items/{item_id}/dispense", response_model=DispensingRead, status_code=status.HTTP_201_CREATED)
def dispense_prescription_item(
    item_id: UUID,
    payload: DispenseCreate,
    profile: Profile = Depends(require_roles(*PHARMACY_STAFF)),
    db: Session = Depends(get_db),
) -> PharmacyDispensing:
    try:
        item = db.scalar(select(PrescriptionItem).where(
            PrescriptionItem.id == item_id
        ).with_for_update())
        if item is None:
            raise HTTPException(status_code=404, detail="Prescription item not found.")
        prescription = db.scalar(select(Prescription).where(
            Prescription.id == item.prescription_id
        ).with_for_update())
        if prescription is None or prescription.status == "cancelled":
            raise HTTPException(status_code=409, detail="Prescription is unavailable or cancelled.")
        already_dispensed = db.scalar(select(func.coalesce(func.sum(PharmacyDispensing.quantity), 0)).where(
            PharmacyDispensing.prescription_item_id == item.id
        )) or 0
        remaining = item.quantity - int(already_dispensed)
        if payload.quantity > remaining:
            raise HTTPException(status_code=409, detail=f"Requested quantity exceeds remaining prescribed quantity ({remaining}).")
        batch = db.scalar(select(MedicineBatch).where(
            MedicineBatch.id == payload.medicine_batch_id
        ).with_for_update())
        if batch is None:
            raise HTTPException(status_code=404, detail="Medicine batch not found.")
        if batch.medicine_id != item.medicine_id:
            raise HTTPException(status_code=422, detail="Selected batch does not match the prescribed medicine.")
        if batch.expires_on and batch.expires_on < date.today():
            raise HTTPException(status_code=409, detail="Expired medicine cannot be dispensed.")
        if batch.quantity_on_hand < payload.quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock in selected batch.")
        batch.quantity_on_hand -= payload.quantity
        dispensing = PharmacyDispensing(
            prescription_item_id=item.id, medicine_batch_id=batch.id,
            quantity=payload.quantity, dispensed_by=profile.id,
        )
        db.add(dispensing)
        db.flush()
        db.add(InventoryTransaction(
            medicine_batch_id=batch.id, quantity_delta=-payload.quantity,
            transaction_type="dispense", reference_id=dispensing.id,
            recorded_by=profile.id, notes=f"Dispensed prescription item {item.id}",
        ))
        new_total = int(already_dispensed) + payload.quantity
        all_items = db.scalars(select(PrescriptionItem).where(
            PrescriptionItem.prescription_id == prescription.id
        )).all()
        totals = {
            row.id: int(db.scalar(select(func.coalesce(func.sum(PharmacyDispensing.quantity), 0)).where(
                PharmacyDispensing.prescription_item_id == row.id
            )) or 0) for row in all_items
        }
        totals[item.id] = new_total
        prescription.status = "dispensed" if all(totals[row.id] >= row.quantity for row in all_items) else "partially_dispensed"
        encounter = db.scalar(select(Encounter).where(Encounter.id == prescription.encounter_id))
        medicine = db.scalar(select(Medicine).where(Medicine.id == item.medicine_id))
        if encounter is not None and medicine is not None and batch.selling_price > 0:
            add_service_charge(
                db, encounter.patient_id, encounter.id,
                f"Pharmacy dispensing {dispensing.id}: {medicine.name}",
                batch.selling_price, payload.quantity,
            )
        _audit(db, profile, "prescription_item.dispensed", "pharmacy_dispensing", dispensing.id, {
            "prescription_id": str(prescription.id), "batch_id": str(batch.id),
            "quantity": payload.quantity, "remaining_after": remaining - payload.quantity,
        })
        notify_roles(db, {"cashier"}, "Pharmacy charge added",
                     "A medicine dispensing transaction added a charge to the patient bill.", "billing")
        notify_roles(db, {"administrator", "pharmacy_staff"}, "Medicine dispensed",
                     "A prescription item was dispensed and pharmacy stock was updated.", "pharmacy", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(dispensing)
        return dispensing
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dispensing conflicts with current stock or prescription state.") from exc
