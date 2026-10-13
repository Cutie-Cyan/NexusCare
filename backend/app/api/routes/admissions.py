from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.models import Admission, AuditLog, Bed, Patient, Profile, Ward
from app.schemas.admission import AdmissionCreate, AdmissionRead, BedRead, DischargeRequest, WardRead

router = APIRouter(tags=["admissions and beds"])

ADMISSION_READ_ROLES = {"administrator", "information_officer", "doctor", "nurse"}
ADMISSION_WRITE_ROLES = ("administrator", "information_officer")


def _require_admission_read_scope(profile: Profile, db: Session):
    roles = set(get_profile_roles(profile.id, db))
    if roles.intersection(ADMISSION_READ_ROLES):
        return None
    if roles == {"patient"}:
        patient = db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id))
        if patient is None:
            return UUID(int=0)
        return patient
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")


def _audit(db: Session, profile: Profile, action: str, resource_id: UUID, details: dict) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id,
        action=action,
        resource_type="admission",
        resource_id=str(resource_id),
        details=details,
    ))


@router.get("/wards", response_model=list[WardRead], summary="List active wards")
def list_wards(
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Ward]:
    roles = set(get_profile_roles(profile.id, db))
    if not roles.intersection(ADMISSION_READ_ROLES | {"patient"}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
    return list(db.scalars(select(Ward).where(Ward.is_active.is_(True)).order_by(Ward.name)).all())


@router.get("/beds", response_model=list[BedRead], summary="List beds and availability")
def list_beds(
    ward_id: UUID | None = None,
    available_only: bool = False,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Bed]:
    roles = set(get_profile_roles(profile.id, db))
    if not roles.intersection(ADMISSION_READ_ROLES | {"patient"}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
    statement = select(Bed).join(Ward, Bed.ward_id == Ward.id).where(Ward.is_active.is_(True))
    if ward_id:
        statement = statement.where(Bed.ward_id == ward_id)
    if available_only:
        statement = statement.where(Bed.status == "available")
    return list(db.scalars(statement.order_by(Bed.ward_id, Bed.bed_number)).all())


@router.get("/admissions", response_model=list[AdmissionRead], summary="List admissions")
def list_admissions(
    patient_id: UUID | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Admission]:
    scope = _require_admission_read_scope(profile, db)
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
    scope = _require_admission_read_scope(profile, db)
    statement = select(Admission).where(Admission.id == admission_id)
    if scope is not None:
        if scope.int == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found.")
        statement = statement.where(Admission.patient_id == scope)
    admission = db.scalar(statement)
    if admission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found.")
    return admission


@router.post("/admissions", response_model=AdmissionRead, status_code=status.HTTP_201_CREATED, summary="Admit a patient")
def create_admission(
    payload: AdmissionCreate,
    profile: Profile = Depends(require_roles(*ADMISSION_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Admission:
    try:
        # Lock the patient row to serialize simultaneous admissions for one patient.
        patient = db.scalar(
            select(Patient).where(Patient.id == payload.patient_id, Patient.is_active.is_(True)).with_for_update()
        )
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active patient not found.")
        existing = db.scalar(
            select(Admission.id).where(Admission.patient_id == patient.id, Admission.status == "admitted").limit(1)
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient already has an active admission.")

        bed = None
        if payload.bed_id is not None:
            bed = db.scalar(select(Bed).where(Bed.id == payload.bed_id).with_for_update())
            if bed is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found.")
            if bed.status != "available":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bed is not available.")
            ward = db.scalar(select(Ward).where(Ward.id == bed.ward_id))
            if ward is None or not ward.is_active:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bed's ward is inactive.")
            bed.status = "occupied"

        if payload.attending_doctor_id is not None:
            doctor = db.scalar(select(Profile).where(
                Profile.id == payload.attending_doctor_id, Profile.is_active.is_(True)
            ))
            if doctor is None or "doctor" not in get_profile_roles(doctor.id, db):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Attending doctor must be an active doctor profile.")

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
        _audit(db, profile, "admission.created", admission.id, {
            "patient_id": str(patient.id), "bed_id": str(bed.id) if bed else None,
        })
        db.commit()
        db.refresh(admission)
        return admission
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admission conflicts with current records.") from exc


@router.post("/admissions/{admission_id}/discharge", response_model=AdmissionRead, summary="Discharge a patient")
def discharge_patient(
    admission_id: UUID,
    payload: DischargeRequest,
    profile: Profile = Depends(require_roles(*ADMISSION_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Admission:
    try:
        admission = db.scalar(select(Admission).where(Admission.id == admission_id).with_for_update())
        if admission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found.")
        if admission.status != "admitted":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admission is not active.")
        if admission.bed_id:
            bed = db.scalar(select(Bed).where(Bed.id == admission.bed_id).with_for_update())
            if bed is not None:
                bed.status = "available"
        admission.status = "discharged"
        admission.discharged_at = datetime.now(timezone.utc)
        admission.discharge_notes = payload.discharge_notes
        _audit(db, profile, "admission.discharged", admission.id, {"bed_id": str(admission.bed_id) if admission.bed_id else None})
        db.commit()
        db.refresh(admission)
        return admission
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not discharge admission.") from exc
