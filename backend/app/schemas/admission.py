from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WardCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    ward_type: str = Field(min_length=2, max_length=60)
    department_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{2,40}", value):
            raise ValueError("Use 2–40 letters, numbers, hyphens, or underscores.")
        return value

    @field_validator("name", "ward_type")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


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


class BedCreate(BaseModel):
    ward_id: UUID
    bed_number: str = Field(min_length=1, max_length=30)
    notes: str | None = None

    @field_validator("bed_number")
    @classmethod
    def strip_bed_number(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Bed number cannot be blank.")
        return value


class BedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ward_id: UUID
    bed_number: str
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AdmissionCreate(BaseModel):
    patient_id: UUID
    bed_id: UUID | None = None
    attending_doctor_id: UUID | None = None
    admission_type: str = Field(default="general", min_length=2, max_length=40)

    @field_validator("admission_type")
    @classmethod
    def normalize_admission_type(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"general", "emergency", "observation", "maternity", "surgical", "other"}:
            raise ValueError("Unsupported admission type.")
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


class BedTransferCreate(BaseModel):
    to_bed_id: UUID
    reason: str | None = Field(default=None, max_length=2000)


class DischargeCreate(BaseModel):
    discharge_notes: str = Field(min_length=3, max_length=5000)

    @field_validator("discharge_notes")
    @classmethod
    def strip_notes(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Discharge notes must contain at least 3 characters.")
        return value
