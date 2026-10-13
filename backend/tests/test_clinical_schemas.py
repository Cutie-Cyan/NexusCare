from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.clinical import (
    DiagnosisCreate, EmergencyEventCreate, EmergencyTriageUpdate,
    EncounterCreate, EncounterUpdate, VitalSignCreate,
)


def test_encounter_complaint_is_trimmed():
    payload = EncounterCreate(patient_id=uuid4(), chief_complaint="  Fever  ")
    assert payload.chief_complaint == "Fever"
    assert payload.encounter_type == "consultation"


def test_encounter_rejects_unknown_type():
    with pytest.raises(ValidationError):
        EncounterCreate(patient_id=uuid4(), encounter_type="invalid")


def test_vitals_require_at_least_one_measurement():
    with pytest.raises(ValidationError, match="at least one"):
        VitalSignCreate()


def test_systolic_pressure_must_exceed_diastolic():
    with pytest.raises(ValidationError, match="Systolic"):
        VitalSignCreate(systolic_bp=90, diastolic_bp=100)


def test_vital_values_are_range_checked():
    with pytest.raises(ValidationError):
        VitalSignCreate(oxygen_saturation=Decimal("140"))


def test_diagnosis_description_is_required_and_trimmed():
    payload = DiagnosisCreate(description="  Acute bronchitis  ", is_primary=True)
    assert payload.description == "Acute bronchitis"
    assert payload.is_primary is True
    with pytest.raises(ValidationError):
        DiagnosisCreate(description=" ")


def test_emergency_complaint_is_trimmed_and_triage_is_validated():
    payload = EmergencyEventCreate(triage_level="red", chief_complaint="  Chest pain ")
    assert payload.chief_complaint == "Chest pain"
    assert payload.status == "waiting"
    with pytest.raises(ValidationError):
        EmergencyEventCreate(triage_level="purple", chief_complaint="Pain")


def test_emergency_triage_status_is_validated():
    with pytest.raises(ValidationError):
        EmergencyTriageUpdate(triage_level="red", status="deleted")


def test_encounter_update_can_close_encounter():
    payload = EncounterUpdate(status="completed")
    assert payload.status == "completed"
