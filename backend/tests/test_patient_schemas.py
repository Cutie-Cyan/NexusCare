from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.patient import PatientCreate, PatientUpdate


def test_patient_create_trims_required_fields():
    patient = PatientCreate(
        medical_record_number=" NC-0001 ",
        first_name=" Ana ",
        last_name=" Santos ",
    )
    assert patient.medical_record_number == "NC-0001"
    assert patient.first_name == "Ana"
    assert patient.last_name == "Santos"


def test_patient_create_rejects_blank_name():
    with pytest.raises(ValidationError):
        PatientCreate(medical_record_number="NC-0001", first_name=" ", last_name="Santos")


def test_patient_create_rejects_future_birth_date():
    with pytest.raises(ValidationError):
        PatientCreate(
            medical_record_number="NC-0001",
            first_name="Ana",
            last_name="Santos",
            date_of_birth=date.today() + timedelta(days=1),
        )


def test_patient_update_supports_partial_updates():
    update = PatientUpdate(phone=" 09171234567 ")
    assert update.model_dump(exclude_unset=True) == {"phone": "09171234567"}


def test_patient_update_rejects_empty_payload_at_route_level():
    assert PatientUpdate().model_dump(exclude_unset=True) == {}
