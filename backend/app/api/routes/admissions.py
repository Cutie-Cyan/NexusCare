from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.core.notifications import notify_roles
from app.db.session import get_db
from app.models import (
    Admission,
    AuditLog,
    Bed,
    Bill,
    Department,
    Patient,
    Payment,
    Profile,
    Ward,
    WardTransfer,
)
from app.schemas.admission import (
    AdmissionCreate,
    AdmissionRead,
    BedCreate,
    BedRead,
    BedTransferCreate,
    DepartmentCreate,
    DepartmentRead,
    DischargeRequest,
    WardCreate,
    WardRead,
)

router = APIRouter(tags=["admissions and beds"])
ADMISSION_READ_ROLES = {
    "administrator", "information_officer", "doctor", "nurse",
    "cashier", "laboratory_staff", "pharmacy_staff",
}
ADMISSION_WRITE_ROLES = ("administrator", "information_officer")
WARD_ADMIN_ROLES = ("administrator",)


def _read_scope(profile: Profile, db: Session) -> UUID | None:
    roles = set(get_profile_roles(profile.id, db))
    if roles.intersection(ADMISSION_READ_ROLES):
        return None
    if roles == {"patient"}:
        patient_id = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        return patient_id or UUID(int=0)
    raise HTTPException(status_code=403, detail="Insufficient permissions.")


def _audit(db: Session, profile: Profile, action: str, resource_type: str, resource_id: UUID, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
    ))


@router.get("/departments", response_model=list[DepartmentRead], summary="List departments")
def list_departments(
    include_inactive: bool = False,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Department]:
    roles = set(get_profile_roles(profile.id, db))
    if not roles.intersection(ADMISSION_READ_ROLES | {"patient"}):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    statement = select(Department)
    if not include_inactive:
        statement = statement.where(Department.is_active.is_(True))
    return list(db.scalars(statement.order_by(Department.name)).all())


@router.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(status_code=409, detail="Department code or name already exists.") from exc


@router.get("/wards", response_model=list[WardRead], summary="List active wards")
def list_wards(
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Ward]:
    roles = set(get_profile_roles(profile.id, db))
    if not roles.intersection(ADMISSION_READ_ROLES | {"patient"}):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return list(db.scalars(select(Ward).where(Ward.is_active.is_(True)).order_by(Ward.name)).all())


@router.post("/wards", response_model=WardRead, status_code=status.HTTP_201_CREATED, summary="Create a ward")
def create_ward(
    payload: WardCreate,
    profile: Profile = Depends(require_roles(*WARD_ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> Ward:
    if payload.department_id and db.scalar(select(Department.id).where(Department.id == payload.department_id)) is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    ward = Ward(**payload.model_dump())
    db.add(ward)
    try:
        db.flush()
        _audit(db, profile, "ward.created", "ward", ward.id, {"code": ward.code})
        db.commit()
        db.refresh(ward)
        return ward
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ward code already exists or ward data conflicts.") from exc


@router.get("/beds", response_model=list[BedRead], summary="List beds and availability")
def list_beds(
    ward_id: UUID | None = None,
    available_only: bool = False,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Bed]:
    roles = set(get_profile_roles(profile.id, db))
    if not roles.intersection(ADMISSION_READ_ROLES | {"patient"}):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    statement = select(Bed).join(Ward, Bed.ward_id == Ward.id).where(Ward.is_active.is_(True))
    if ward_id:
        statement = statement.where(Bed.ward_id == ward_id)
    if available_only:
        statement = statement.where(Bed.status == "available")
    return list(db.scalars(statement.order_by(Bed.ward_id, Bed.bed_number)).all())


@router.post("/beds", response_model=BedRead, status_code=status.HTTP_201_CREATED, summary="Create a bed")
def create_bed(
    payload: BedCreate,
    profile: Profile = Depends(require_roles(*WARD_ADMIN_ROLES)),
    db: Session = Depends(get_db),
) -> Bed:
    ward = db.scalar(select(Ward).where(Ward.id == payload.ward_id, Ward.is_active.is_(True)))
    if ward is None:
        raise HTTPException(status_code=404, detail="Active ward not found.")
    bed = Bed(**payload.model_dump(), status="available")
    db.add(bed)
    try:
        db.flush()
        _audit(db, profile, "bed.created", "bed", bed.id, {"ward_id": str(ward.id), "bed_number": bed.bed_number})
        db.commit()
        db.refresh(bed)
        return bed
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That bed number already exists in this ward.") from exc


@router.get("/admissions", response_model=list[AdmissionRead], summary="List admissions")
def list_admissions(
    patient_id: UUID | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Admission]:
    scope = _read_scope(profile, db)
    statement = select(Admission)
    if scope is not None:
        if scope.int == 0:
            return []
        statement = statement.where(Admission.patient_id == scope)
    elif patient_id:
        statement = statement.where(Admission.patient_id == patient_id)
    if active_only:
        statement = statement.where(Admission.status == "admitted")
    return list(db.scalars(statement.order_by(Admission.admitted_at.desc()).offset(offset).limit(limit)).all())


@router.get("/admissions/{admission_id}", response_model=AdmissionRead, summary="Get an admission")
def get_admission(
    admission_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Admission:
    scope = _read_scope(profile, db)
    statement = select(Admission).where(Admission.id == admission_id)
    if scope is not None:
        if scope.int == 0:
            raise HTTPException(status_code=404, detail="Admission not found.")
        statement = statement.where(Admission.patient_id == scope)
    admission = db.scalar(statement)
    if admission is None:
        raise HTTPException(status_code=404, detail="Admission not found.")
    return admission


@router.post("/admissions", response_model=AdmissionRead, status_code=status.HTTP_201_CREATED, summary="Admit a patient")
def create_admission(
    payload: AdmissionCreate,
    profile: Profile = Depends(require_roles(*ADMISSION_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Admission:
    try:
        patient = db.scalar(select(Patient).where(
            Patient.id == payload.patient_id, Patient.is_active.is_(True)
        ).with_for_update())
        if patient is None:
            raise HTTPException(status_code=404, detail="Active patient not found.")
        existing = db.scalar(select(Admission.id).where(
            Admission.patient_id == patient.id, Admission.status == "admitted"
        ).limit(1))
        if existing:
            raise HTTPException(status_code=409, detail="Patient already has an active admission.")

        bed = None
        if payload.bed_id:
            bed = db.scalar(select(Bed).where(Bed.id == payload.bed_id).with_for_update())
            if bed is None:
                raise HTTPException(status_code=404, detail="Bed not found.")
            if bed.status != "available":
                raise HTTPException(status_code=409, detail="Bed is not available.")
            ward = db.scalar(select(Ward).where(Ward.id == bed.ward_id, Ward.is_active.is_(True)))
            if ward is None:
                raise HTTPException(status_code=409, detail="Bed's ward is inactive.")
            bed.status = "occupied"

        if payload.attending_doctor_id:
            doctor = db.scalar(select(Profile).where(
                Profile.id == payload.attending_doctor_id, Profile.is_active.is_(True)
            ))
            if doctor is None or "doctor" not in get_profile_roles(doctor.id, db):
                raise HTTPException(status_code=422, detail="Attending doctor must be an active doctor profile.")

        admission = Admission(
            patient_id=patient.id,
            bed_id=bed.id if bed else None,
            admitted_by=profile.id,
            attending_doctor_id=payload.attending_doctor_id,
            admission_type=payload.admission_type,
            status="admitted",
        )
        db.add(admission)
        db.flush()
        _audit(db, profile, "admission.created", "admission", admission.id, {
            "patient_id": str(patient.id), "bed_id": str(bed.id) if bed else None,
        })
        notify_roles(db, {"doctor", "nurse"}, "New admission",
                     "A patient admission was recorded. Open the authorized admissions queue for details.",
                     "admission", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(admission)
        return admission
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Admission conflicts with current records.") from exc


@router.post("/admissions/{admission_id}/transfer", response_model=AdmissionRead, summary="Transfer a patient to another bed")
def transfer_admission(
    admission_id: UUID,
    payload: BedTransferCreate,
    profile: Profile = Depends(require_roles(*ADMISSION_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Admission:
    try:
        admission = db.scalar(select(Admission).where(
            Admission.id == admission_id, Admission.status == "admitted"
        ).with_for_update())
        if admission is None:
            raise HTTPException(status_code=404, detail="Active admission not found.")
        if admission.bed_id is None:
            raise HTTPException(status_code=409, detail="Admission has no assigned bed.")
        bed_ids = sorted({admission.bed_id, payload.to_bed_id}, key=str)
        beds = db.scalars(select(Bed).where(Bed.id.in_(bed_ids)).order_by(Bed.id).with_for_update()).all()
        bed_map = {bed.id: bed for bed in beds}
        old_bed, new_bed = bed_map.get(admission.bed_id), bed_map.get(payload.to_bed_id)
        if old_bed is None or new_bed is None:
            raise HTTPException(status_code=404, detail="Current or destination bed not found.")
        if old_bed.id == new_bed.id:
            raise HTTPException(status_code=400, detail="Destination bed must be different.")
        ward = db.scalar(select(Ward).where(Ward.id == new_bed.ward_id, Ward.is_active.is_(True)))
        if ward is None:
            raise HTTPException(status_code=409, detail="Destination ward is inactive.")
        if new_bed.status != "available":
            raise HTTPException(status_code=409, detail="Destination bed is not available.")
        new_bed.status = "occupied"
        old_bed.status = "available"
        admission.bed_id = new_bed.id
        db.add(WardTransfer(
            admission_id=admission.id,
            from_bed_id=old_bed.id,
            to_bed_id=new_bed.id,
            requested_by=profile.id,
            reason=payload.reason.strip() or None if payload.reason else None,
            status="completed",
        ))
        _audit(db, profile, "admission.transferred", "admission", admission.id, {
            "from_bed_id": str(old_bed.id), "to_bed_id": str(new_bed.id),
        })
        notify_roles(db, {"doctor", "nurse"}, "Ward transfer recorded",
                     "A ward or bed transfer was completed.", "admission", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(admission)
        return admission
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not transfer admission.") from exc


@router.post("/admissions/{admission_id}/discharge", response_model=AdmissionRead, summary="Discharge a patient")
def discharge_patient(
    admission_id: UUID,
    payload: DischargeRequest,
    profile: Profile = Depends(require_roles(*ADMISSION_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Admission:
    try:
        admission = db.scalar(select(Admission).where(
            Admission.id == admission_id, Admission.status == "admitted"
        ).with_for_update())
        if admission is None:
            raise HTTPException(status_code=404, detail="Active admission not found.")
        patient_bills = db.scalars(select(Bill).where(
            Bill.patient_id == admission.patient_id,
            Bill.status.in_(["open", "partially_paid"]),
        ).with_for_update()).all()
        outstanding = Decimal("0.00")
        for bill in patient_bills:
            paid = Decimal(str(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.bill_id == bill.id, Payment.status == "posted"
            )) or 0))
            outstanding += max(Decimal("0.00"), bill.total - paid)
        if outstanding > 0:
            if not payload.billing_exception_reason:
                raise HTTPException(status_code=409, detail=f"Discharge requires settlement or an administrator-authorized billing exception. Outstanding balance: {outstanding}.")
            if "administrator" not in get_profile_roles(profile.id, db):
                raise HTTPException(status_code=403, detail="Only an administrator may authorize discharge with an outstanding balance.")
        if admission.bed_id:
            bed = db.scalar(select(Bed).where(Bed.id == admission.bed_id).with_for_update())
            if bed is not None:
                bed.status = "available"
        admission.status = "discharged"
        admission.discharged_at = datetime.now(UTC)
        admission.discharge_notes = payload.discharge_notes
        _audit(db, profile, "admission.discharged", "admission", admission.id, {
            "patient_id": str(admission.patient_id),
            "bed_id": str(admission.bed_id) if admission.bed_id else None,
            "outstanding_balance_at_discharge": str(outstanding),
            "billing_exception_reason": payload.billing_exception_reason,
        })
        notify_roles(db, {"doctor", "nurse", "cashier"}, "Discharge recorded",
                     "A discharge was completed and bed availability was updated.", "admission", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(admission)
        return admission
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not discharge admission.") from exc
