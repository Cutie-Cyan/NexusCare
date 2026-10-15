from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile, get_profile_roles, require_roles
from app.core.notifications import notify_roles
from app.db.session import get_db
from app.models import (
    Admission,
    Appointment,
    AuditLog,
    Bill,
    Diagnosis,
    Encounter,
    LaboratoryOrder,
    LaboratoryResult,
    Patient,
    Payment,
    Prescription,
    PrescriptionItem,
    Profile,
    VitalSign,
)
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



@router.get("/{patient_id}/history", summary="Retrieve a patient's authorized medical history")
def get_patient_history(
    patient_id: UUID,
    profile: Profile = Depends(get_current_profile),
    db: Session = Depends(get_db),
) -> dict:
    role_codes = set(get_profile_roles(profile.id, db))
    patient = db.scalar(select(Patient).where(Patient.id == patient_id, Patient.is_active.is_(True)))
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    is_patient_self = (
        "patient" in role_codes
        and not role_codes.intersection(PATIENT_STAFF_READ_ROLES)
    )
    is_administrator = "administrator" in role_codes
    if is_patient_self:
        if patient.patient_profile_id != profile.id:
            raise HTTPException(status_code=404, detail="Patient not found.")
    elif not (is_administrator or role_codes.intersection({"doctor", "nurse"})):
        # Reception, cashier, laboratory, and pharmacy roles must not receive a
        # complete clinical history through this endpoint.
        raise HTTPException(status_code=403, detail="Clinical history access is not permitted for this role.")

    encounter_statement = select(Encounter).where(Encounter.patient_id == patient.id)
    if not (is_patient_self or is_administrator):
        from sqlalchemy import or_
        scope_conditions = [Encounter.clinician_id == profile.id]
        if profile.department_id is not None:
            scope_conditions.append(Encounter.department_id == profile.department_id)
        encounter_statement = encounter_statement.where(or_(*scope_conditions))
    encounters = db.scalars(
        encounter_statement.order_by(Encounter.started_at.desc())
    ).all()
    if not (is_patient_self or is_administrator) and not encounters:
        raise HTTPException(status_code=404, detail="Patient history not found for your assigned care scope.")
    encounter_ids = [row.id for row in encounters]
    diagnoses = db.scalars(select(Diagnosis).where(
        Diagnosis.encounter_id.in_(encounter_ids)
    ).order_by(Diagnosis.id)).all() if encounter_ids else []
    vitals = db.scalars(select(VitalSign).where(
        VitalSign.encounter_id.in_(encounter_ids)
    ).order_by(VitalSign.recorded_at.desc())) .all() if encounter_ids else []
    lab_rows = db.execute(
        select(LaboratoryOrder, LaboratoryResult)
        .join(LaboratoryResult, LaboratoryResult.order_id == LaboratoryOrder.id)
        .where(LaboratoryOrder.encounter_id.in_(encounter_ids), LaboratoryResult.status.in_(["verified", "released"]))
        .order_by(LaboratoryResult.created_at.desc())
    ).all() if encounter_ids else []
    prescription_rows = db.scalars(select(Prescription).where(
        Prescription.encounter_id.in_(encounter_ids)
    ).order_by(Prescription.created_at.desc())).all() if encounter_ids else []
    prescription_ids = [row.id for row in prescription_rows]
    prescription_items = db.scalars(select(PrescriptionItem).where(
        PrescriptionItem.prescription_id.in_(prescription_ids)
    )).all() if prescription_ids else []
    admission_statement = select(Admission).where(Admission.patient_id == patient.id)
    appointment_statement = select(Appointment).where(Appointment.patient_id == patient.id)
    if not (is_patient_self or is_administrator):
        encounter_admission_ids = [row.admission_id for row in encounters if row.admission_id]
        from sqlalchemy import or_
        admission_conditions = [Admission.attending_doctor_id == profile.id]
        if encounter_admission_ids:
            admission_conditions.append(Admission.id.in_(encounter_admission_ids))
        admission_statement = admission_statement.where(or_(*admission_conditions))
        appointment_conditions = [Appointment.clinician_id == profile.id]
        if profile.department_id is not None:
            appointment_conditions.append(Appointment.department_id == profile.department_id)
        appointment_statement = appointment_statement.where(or_(*appointment_conditions))
    admissions = db.scalars(
        admission_statement.order_by(Admission.admitted_at.desc())
    ).all()
    appointments = db.scalars(
        appointment_statement.order_by(Appointment.scheduled_at.desc()).limit(100)
    ).all()

    result = {
        "patient": PatientRead.model_validate(patient).model_dump(mode="json"),
        "encounters": [{
            "id": str(row.id), "encounter_type": row.encounter_type,
            "status": row.status, "chief_complaint": row.chief_complaint,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "ended_at": row.ended_at.isoformat() if row.ended_at else None,
        } for row in encounters],
        "diagnoses": [{
            "id": str(row.id), "encounter_id": str(row.encounter_id),
            "code": row.code, "description": row.description,
            "is_primary": row.is_primary,
        } for row in diagnoses],
        "vital_signs": [{
            "id": str(row.id), "encounter_id": str(row.encounter_id),
            "temperature_c": row.temperature_c, "pulse_bpm": row.pulse_bpm,
            "respiratory_rate": row.respiratory_rate,
            "systolic_bp": row.systolic_bp, "diastolic_bp": row.diastolic_bp,
            "oxygen_saturation": row.oxygen_saturation,
            "weight_kg": row.weight_kg, "height_cm": row.height_cm,
            "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
        } for row in vitals],
        "released_laboratory_results": [{
            "order_id": str(order.id), "result_id": str(lab_result.id),
            "test_id": str(order.test_id), "status": lab_result.status,
            "result_text": lab_result.result_text, "result_data": lab_result.result_data,
            "released_at": lab_result.verified_at.isoformat() if lab_result.verified_at else None,
        } for order, lab_result in lab_rows],
        "prescriptions": [{
            "id": str(row.id), "encounter_id": str(row.encounter_id),
            "status": row.status, "instructions": row.instructions,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "items": [{
                "medicine_id": str(item.medicine_id), "dose": item.dose,
                "route": item.route, "frequency": item.frequency,
                "duration": item.duration, "quantity": item.quantity,
                "instructions": item.instructions,
            } for item in prescription_items if item.prescription_id == row.id],
        } for row in prescription_rows],
        "admissions": [{
            "id": str(row.id), "status": row.status, "admission_type": row.admission_type,
            "bed_id": str(row.bed_id) if row.bed_id else None,
            "admitted_at": row.admitted_at.isoformat() if row.admitted_at else None,
            "discharged_at": row.discharged_at.isoformat() if row.discharged_at else None,
        } for row in admissions],
        "appointments": [{
            "id": str(row.id), "scheduled_at": row.scheduled_at.isoformat(),
            "status": row.status, "reason": row.reason,
            "clinician_id": str(row.clinician_id) if row.clinician_id else None,
        } for row in appointments],
    }
    if role_codes.intersection({"administrator", "information_officer", "cashier", "patient"}):
        bills = db.scalars(select(Bill).where(
            Bill.patient_id == patient.id
        ).order_by(Bill.created_at.desc())).all()
        result["bills"] = [{
            "id": str(bill.id), "bill_number": bill.bill_number, "status": bill.status,
            "subtotal": bill.subtotal, "adjustments": bill.adjustments, "total": bill.total,
            "payments": [{
                "id": str(payment.id), "amount": payment.amount,
                "payment_method": payment.payment_method, "status": payment.status,
                "receipt_number": payment.receipt_number,
                "received_at": payment.received_at.isoformat() if payment.received_at else None,
            } for payment in db.scalars(select(Payment).where(Payment.bill_id == bill.id).order_by(Payment.received_at.desc())).all()],
        } for bill in bills]
    return result


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
