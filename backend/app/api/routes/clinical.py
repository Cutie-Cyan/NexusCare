from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.db.session import get_db
from app.models import (
    Admission, AuditLog, Diagnosis, EmergencyEvent, Encounter, Patient, Profile,
    VitalSign,
)
from app.schemas.clinical import (
    DiagnosisCreate, DiagnosisRead, EmergencyEventCreate, EmergencyEventRead,
    EmergencyTriageUpdate, EncounterCreate, EncounterRead, EncounterUpdate,
    VitalSignCreate, VitalSignRead,
)

router = APIRouter(tags=["clinical encounters and emergency"])

CLINICAL_READ_ROLES = {"administrator", "information_officer", "doctor", "nurse"}
CLINICAL_WRITE_ROLES = ("doctor", "nurse")
ENCOUNTER_CREATE_ROLES = ("administrator", "information_officer", "doctor", "nurse")
EMERGENCY_CREATE_ROLES = ("administrator", "information_officer", "doctor", "nurse")


def _roles(profile: Profile, db: Session) -> set[str]:
    return set(get_profile_roles(profile.id, db))


def _patient_scope(profile: Profile, roles: set[str], db: Session) -> UUID | None:
    if roles.intersection(CLINICAL_READ_ROLES):
        return None
    if roles == {"patient"}:
        return db.scalar(select(Patient.id).where(Patient.patient_profile_id == profile.id)) or UUID(int=0)
    raise HTTPException(status_code=403, detail="Insufficient permissions.")


def _audit(
    db: Session, profile: Profile, action: str, resource_type: str,
    resource_id: UUID, details: dict | None = None,
) -> None:
    db.add(AuditLog(
        actor_profile_id=profile.id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
    ))


def _get_encounter_or_404(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.scalar(select(Encounter).where(Encounter.id == encounter_id))
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    return encounter


def _ensure_encounter_read_access(
    encounter: Encounter, profile: Profile, roles: set[str], db: Session,
) -> None:
    scope = _patient_scope(profile, roles, db)
    if scope is not None and encounter.patient_id != scope:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    if scope is None and not roles.intersection(CLINICAL_READ_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")


@router.get("/encounters", response_model=list[EncounterRead], summary="List clinical encounters")
def list_encounters(
    patient_id: UUID | None = None,
    encounter_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Encounter]:
    roles = _roles(profile, db)
    scope = _patient_scope(profile, roles, db)
    statement = select(Encounter)
    if scope is not None:
        if scope.int == 0:
            return []
        statement = statement.where(Encounter.patient_id == scope)
    elif patient_id is not None:
        statement = statement.where(Encounter.patient_id == patient_id)
    if encounter_status:
        if encounter_status not in {"open", "in_progress", "completed", "cancelled"}:
            raise HTTPException(status_code=422, detail="Unsupported encounter status.")
        statement = statement.where(Encounter.status == encounter_status)
    return list(db.scalars(
        statement.order_by(Encounter.started_at.desc()).offset(offset).limit(limit)
    ).all())


@router.post(
    "/encounters", response_model=EncounterRead, status_code=status.HTTP_201_CREATED,
    summary="Create a clinical encounter",
)
def create_encounter(
    payload: EncounterCreate,
    profile: Profile = Depends(require_roles(*ENCOUNTER_CREATE_ROLES)),
    db: Session = Depends(get_db),
) -> Encounter:
    patient = db.scalar(select(Patient).where(
        Patient.id == payload.patient_id, Patient.is_active.is_(True)
    ))
    if patient is None:
        raise HTTPException(status_code=404, detail="Active patient not found.")
    if payload.admission_id:
        admission = db.scalar(select(Admission).where(
            Admission.id == payload.admission_id,
            Admission.patient_id == patient.id,
            Admission.status == "admitted",
        ))
        if admission is None:
            raise HTTPException(status_code=422, detail="Admission must be active and belong to this patient.")
    if payload.department_id:
        from app.models import Department
        department = db.scalar(select(Department.id).where(
            Department.id == payload.department_id, Department.is_active.is_(True)
        ))
        if department is None:
            raise HTTPException(status_code=422, detail="Active department not found.")
    roles = _roles(profile, db)
    clinician_id = profile.id if roles.intersection({"doctor", "nurse"}) else None
    encounter = Encounter(
        **payload.model_dump(),
        clinician_id=clinician_id,
        status="open",
    )
    db.add(encounter)
    try:
        db.flush()
        _audit(db, profile, "encounter.created", "encounter", encounter.id, {
            "patient_id": str(patient.id), "encounter_type": encounter.encounter_type,
        })
        db.commit()
        db.refresh(encounter)
        return encounter
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Encounter conflicts with existing records.") from exc


@router.get("/encounters/{encounter_id}", response_model=EncounterRead, summary="Get an encounter")
def get_encounter(
    encounter_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> Encounter:
    encounter = _get_encounter_or_404(db, encounter_id)
    _ensure_encounter_read_access(encounter, profile, _roles(profile, db), db)
    return encounter


@router.patch("/encounters/{encounter_id}", response_model=EncounterRead, summary="Update encounter notes or status")
def update_encounter(
    encounter_id: UUID,
    payload: EncounterUpdate,
    profile: Profile = Depends(require_roles(*CLINICAL_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> Encounter:
    encounter = db.scalar(select(Encounter).where(
        Encounter.id == encounter_id
    ).with_for_update())
    if encounter is None:
        raise HTTPException(status_code=404, detail="Encounter not found.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields supplied.")
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Closed encounters cannot be changed.")
    if changes.get("status") == "cancelled" and encounter.status != "open":
        raise HTTPException(status_code=409, detail="Only open encounters can be cancelled.")
    if changes.get("status") == "completed":
        encounter.ended_at = datetime.now(timezone.utc)
    elif changes.get("status") in {"open", "in_progress"}:
        encounter.ended_at = None
    for field, value in changes.items():
        setattr(encounter, field, value)
    _audit(db, profile, "encounter.updated", "encounter", encounter.id, {
        "fields": sorted(changes.keys()),
    })
    db.commit()
    db.refresh(encounter)
    return encounter


@router.get(
    "/encounters/{encounter_id}/vitals", response_model=list[VitalSignRead],
    summary="List vital-sign observations",
)
def list_vitals(
    encounter_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[VitalSign]:
    encounter = _get_encounter_or_404(db, encounter_id)
    _ensure_encounter_read_access(encounter, profile, _roles(profile, db), db)
    return list(db.scalars(
        select(VitalSign).where(VitalSign.encounter_id == encounter_id)
        .order_by(VitalSign.recorded_at.desc())
    ).all())


@router.post(
    "/encounters/{encounter_id}/vitals", response_model=VitalSignRead,
    status_code=status.HTTP_201_CREATED, summary="Record vital signs",
)
def create_vitals(
    encounter_id: UUID,
    payload: VitalSignCreate,
    profile: Profile = Depends(require_roles(*CLINICAL_WRITE_ROLES)),
    db: Session = Depends(get_db),
) -> VitalSign:
    encounter = _get_encounter_or_404(db, encounter_id)
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot add vital signs to a closed encounter.")
    record = VitalSign(encounter_id=encounter.id, recorded_by=profile.id, **payload.model_dump())
    db.add(record)
    db.flush()
    _audit(db, profile, "vitals.recorded", "vital_signs", record.id, {
        "encounter_id": str(encounter.id),
    })
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/encounters/{encounter_id}/diagnoses", response_model=list[DiagnosisRead],
    summary="List encounter diagnoses",
)
def list_diagnoses(
    encounter_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[Diagnosis]:
    encounter = _get_encounter_or_404(db, encounter_id)
    _ensure_encounter_read_access(encounter, profile, _roles(profile, db), db)
    return list(db.scalars(
        select(Diagnosis).where(Diagnosis.encounter_id == encounter_id)
        .order_by(Diagnosis.is_primary.desc(), Diagnosis.description)
    ).all())


@router.post(
    "/encounters/{encounter_id}/diagnoses", response_model=DiagnosisRead,
    status_code=status.HTTP_201_CREATED, summary="Record an encounter diagnosis",
)
def create_diagnosis(
    encounter_id: UUID,
    payload: DiagnosisCreate,
    profile: Profile = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
) -> Diagnosis:
    encounter = _get_encounter_or_404(db, encounter_id)
    if encounter.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Cannot add a diagnosis to a closed encounter.")
    if payload.is_primary:
        db.query(Diagnosis).filter(
            Diagnosis.encounter_id == encounter_id,
            Diagnosis.is_primary.is_(True),
        ).update({Diagnosis.is_primary: False}, synchronize_session=False)
    diagnosis = Diagnosis(
        encounter_id=encounter.id,
        recorded_by=profile.id,
        **payload.model_dump(),
    )
    db.add(diagnosis)
    db.flush()
    _audit(db, profile, "diagnosis.recorded", "diagnosis", diagnosis.id, {
        "encounter_id": str(encounter.id), "is_primary": diagnosis.is_primary,
    })
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


@router.get(
    "/emergency-events", response_model=list[EmergencyEventRead],
    summary="List emergency-room events",
)
def list_emergency_events(
    event_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> list[EmergencyEvent]:
    roles = _roles(profile, db)
    scope = _patient_scope(profile, roles, db)
    statement = select(EmergencyEvent)
    if scope is not None:
        if scope.int == 0:
            return []
        statement = statement.where(EmergencyEvent.patient_id == scope)
    if event_status:
        if event_status not in {"waiting", "in_treatment", "transferred", "completed"}:
            raise HTTPException(status_code=422, detail="Unsupported emergency status.")
        statement = statement.where(EmergencyEvent.status == event_status)
    return list(db.scalars(
        statement.order_by(EmergencyEvent.arrived_at.desc()).offset(offset).limit(limit)
    ).all())


@router.post(
    "/emergency-events", response_model=EmergencyEventRead,
    status_code=status.HTTP_201_CREATED, summary="Register an emergency-room event",
)
def create_emergency_event(
    payload: EmergencyEventCreate,
    profile: Profile = Depends(require_roles(*EMERGENCY_CREATE_ROLES)),
    db: Session = Depends(get_db),
) -> EmergencyEvent:
    patient = None
    if payload.patient_id:
        patient = db.scalar(select(Patient).where(
            Patient.id == payload.patient_id, Patient.is_active.is_(True)
        ))
        if patient is None:
            raise HTTPException(status_code=404, detail="Active patient not found.")
    encounter = None
    if payload.encounter_id:
        encounter = db.scalar(select(Encounter).where(Encounter.id == payload.encounter_id))
        if encounter is None:
            raise HTTPException(status_code=404, detail="Encounter not found.")
        if patient and encounter.patient_id != patient.id:
            raise HTTPException(status_code=422, detail="Encounter does not belong to the selected patient.")
        patient = patient or db.scalar(select(Patient).where(Patient.id == encounter.patient_id))
    elif patient:
        roles = _roles(profile, db)
        encounter = Encounter(
            patient_id=patient.id,
            clinician_id=profile.id if roles.intersection({"doctor", "nurse"}) else None,
            encounter_type="emergency",
            status="open",
            chief_complaint=payload.chief_complaint,
        )
        db.add(encounter)
        db.flush()
    roles = _roles(profile, db)
    event = EmergencyEvent(
        patient_id=patient.id if patient else None,
        encounter_id=encounter.id if encounter else None,
        triage_level=payload.triage_level,
        chief_complaint=payload.chief_complaint,
        status=payload.status,
        triaged_by=profile.id if roles.intersection({"doctor", "nurse"}) else None,
    )
    db.add(event)
    db.flush()
    _audit(db, profile, "emergency_event.created", "emergency_event", event.id, {
        "patient_id": str(patient.id) if patient else None,
        "triage_level": event.triage_level,
    })
    db.commit()
    db.refresh(event)
    return event


@router.patch(
    "/emergency-events/{event_id}/triage", response_model=EmergencyEventRead,
    summary="Update emergency triage and status",
)
def update_emergency_triage(
    event_id: UUID,
    payload: EmergencyTriageUpdate,
    profile: Profile = Depends(require_roles("doctor", "nurse")),
    db: Session = Depends(get_db),
) -> EmergencyEvent:
    event = db.scalar(select(EmergencyEvent).where(
        EmergencyEvent.id == event_id
    ).with_for_update())
    if event is None:
        raise HTTPException(status_code=404, detail="Emergency event not found.")
    event.triage_level = payload.triage_level
    event.status = payload.status
    event.triaged_by = profile.id
    _audit(db, profile, "emergency_event.triaged", "emergency_event", event.id, {
        "triage_level": event.triage_level, "status": event.status,
    })
    db.commit()
    db.refresh(event)
    return event
