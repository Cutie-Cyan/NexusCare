from uuid import uuid4

from pydantic import ValidationError
import pytest

from app.schemas.admission import AdmissionCreate, DischargeRequest


def test_admission_type_is_normalized():
    payload = AdmissionCreate(patient_id=uuid4(), admission_type=" General ")
    assert payload.admission_type == "general"


def test_admission_type_cannot_be_blank():
    with pytest.raises(ValidationError):
        AdmissionCreate(patient_id=uuid4(), admission_type="  ")


def test_bed_assignment_is_optional():
    payload = AdmissionCreate(patient_id=uuid4())
    assert payload.bed_id is None


def test_discharge_notes_are_trimmed():
    payload = DischargeRequest(discharge_notes="  Stable for discharge  ")
    assert payload.discharge_notes == "Stable for discharge"


def test_blank_discharge_notes_become_none():
    payload = DischargeRequest(discharge_notes="  ")
    assert payload.discharge_notes is None
