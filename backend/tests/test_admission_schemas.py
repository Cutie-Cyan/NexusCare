from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.admission import (
    AdmissionCreate, BedCreate, BedTransferCreate, DischargeCreate, WardCreate,
)


def test_admission_type_is_normalized():
    payload = AdmissionCreate(patient_id=uuid4(), admission_type=" GENERAL ")
    assert payload.admission_type == "general"


def test_invalid_admission_type_is_rejected():
    with pytest.raises(ValidationError):
        AdmissionCreate(patient_id=uuid4(), admission_type="unexpected")


def test_ward_and_bed_fields_are_trimmed():
    ward = WardCreate(code=" GEN ", name=" General Ward ", ward_type=" inpatient ")
    bed = BedCreate(ward_id=uuid4(), bed_number=" 101 ")
    assert ward.code == "GEN"
    assert ward.name == "General Ward"
    assert bed.bed_number == "101"


def test_discharge_notes_cannot_be_blank():
    with pytest.raises(ValidationError):
        DischargeCreate(discharge_notes="  ")


def test_transfer_requires_destination_bed():
    with pytest.raises(ValidationError):
        BedTransferCreate(to_bed_id="not-a-uuid")
