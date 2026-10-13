from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.core.notifications import notify_roles
from app.models import AuditLog, Patient, Profile
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])

PATIENT_STAFF_READ_ROLES = {
    "administrator", "information_officer", "doctor", "nurse",
    "cashier", "laboratory_staff", "pharmacy_staff",
}
PATIENT_MANAGEMENT_ROLES = ("administrator", "information_officer")


def _patient_scope(profile: Profile, role_codes: set[str]):
    """Patients may only see their own linked record; staff access is role-gated."""
    if role_codes == {"patient"} or "patient" in role_codes and not role_codes.intersection(PATIENT_STAFF_READ_ROLES):
        return Patient.patient_profile_id == profile.id
    if not role_codes.intersection(PATIENT_STAFF_READ_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
    return None


def _audit(db: Session, profile: Profile, action: str, patient: Patient, details: dict | None = None) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id,
        action=action,
        resource_type="patient",
        resource_id=str(patient.id),
        details=details or {},
    ))


@router.get("", response_model=list[PatientRead], summary="Search and list patients")
def list_patients(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Patient]:
    roles = set(get_profile_roles(profile.id, db))
    scope = _patient_scope(profile, roles)
    statement = select(Patient).where(Patient.is_active.is_(True))
    if scope is not None:
        statement = statement.where(scope)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(or_(
            Patient.medical_record_number.ilike(term),
            Patient.first_name.ilike(term),
            Patient.middle_name.ilike(term),
            Patient.last_name.ilike(term),
        ))
    statement = statement.order_by(Patient.last_name, Patient.first_name).offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/{patient_id}", response_model=PatientRead, summary="Get a patient record")
def get_patient(
    patient_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Patient:
    roles = set(get_profile_roles(profile.id, db))
    scope = _patient_scope(profile, roles)
    statement = select(Patient).where(Patient.id == patient_id, Patient.is_active.is_(True))
    if scope is not None:
        statement = statement.where(scope)
    patient = db.scalar(statement)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return patient


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED, summary="Register a patient")
def create_patient(
    payload: PatientCreate,
    profile: Profile = Depends(require_roles(*PATIENT_MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> Patient:
    patient = Patient(**payload.model_dump())
    db.add(patient)
    try:
        db.flush()
        _audit(db, profile, "patient.created", patient, {"medical_record_number": patient.medical_record_number})
        notify_roles(db, {"administrator", "doctor", "nurse", "information_officer"},
                     "New patient registered", "A new patient record is available to authorized staff.",
                     "patient_registration", exclude_profile_id=profile.id)
        db.commit()
        db.refresh(patient)
        return patient
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A patient with that medical record number already exists.",
        ) from exc


@router.patch("/{patient_id}", response_model=PatientRead, summary="Update patient demographics")
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    profile: Profile = Depends(require_roles(*PATIENT_MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.id == patient_id, Patient.is_active.is_(True)))
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields supplied.")
    for field, value in changes.items():
        setattr(patient, field, value)
    try:
        _audit(db, profile, "patient.updated", patient, {"fields": sorted(changes.keys())})
        db.commit()
        db.refresh(patient)
        return patient
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient update conflicts with existing data.") from exc


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate a patient record")
def deactivate_patient(
    patient_id: UUID,
    profile: Profile = Depends(require_roles(*PATIENT_MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
) -> None:
    patient = db.scalar(select(Patient).where(Patient.id == patient_id, Patient.is_active.is_(True)))
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    patient.is_active = False
    _audit(db, profile, "patient.deactivated", patient)
    db.commit()
    return None
