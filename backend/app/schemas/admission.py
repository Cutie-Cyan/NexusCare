from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdmissionCreate(BaseModel):
    patient_id: UUID
    bed_id: UUID | None = None
    attending_doctor_id: UUID | None = None
    admission_type: str = Field(default="general", min_length=2, max_length=40)

    @field_validator("admission_type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Admission type cannot be blank.")
        return value


class DischargeRequest(BaseModel):
    discharge_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("discharge_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class AdmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    bed_id: UUID | None
    admitted_by: UUID | None
    attending_doctor_id: UUID | None
    admission_type: str
    status: str
    admitted_at: datetime
    discharged_at: datetime | None
    discharge_notes: str | None
    created_at: datetime
    updated_at: datetime


class BedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ward_id: UUID
    bed_number: str
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class WardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID | None
    code: str
    name: str
    ward_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
