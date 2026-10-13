from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EncounterType = Literal["emergency", "consultation", "inpatient", "outpatient", "follow_up", "observation"]
EncounterStatus = Literal["open", "in_progress", "completed", "cancelled"]
TriageLevel = Literal["red", "orange", "yellow", "green", "blue"]
EmergencyStatus = Literal["waiting", "in_treatment", "transferred", "completed"]


class EncounterCreate(BaseModel):
    patient_id: UUID
    admission_id: UUID | None = None
    department_id: UUID | None = None
    encounter_type: EncounterType = "consultation"
    chief_complaint: str | None = Field(default=None, max_length=5000)
    clinical_notes: str | None = Field(default=None, max_length=10000)

    @field_validator("chief_complaint", "clinical_notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class EncounterUpdate(BaseModel):
    status: EncounterStatus | None = None
    chief_complaint: str | None = Field(default=None, max_length=5000)
    clinical_notes: str | None = Field(default=None, max_length=10000)

    @field_validator("chief_complaint", "clinical_notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class EncounterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    admission_id: UUID | None
    department_id: UUID | None
    clinician_id: UUID | None
    encounter_type: str
    status: str
    chief_complaint: str | None
    clinical_notes: str | None
    started_at: datetime
    ended_at: datetime
    created_at: datetime
    updated_at: datetime


class VitalSignCreate(BaseModel):
    temperature_c: Decimal | None = Field(default=None, ge=25, le=45, max_digits=4, decimal_places=1)
    pulse_bpm: int | None = Field(default=None, ge=20, le=250)
    respiratory_rate: int | None = Field(default=None, ge=4, le=80)
    systolic_bp: int | None = Field(default=None, ge=40, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)
    oxygen_saturation: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=500, max_digits=6, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, gt=0, le=300, max_digits=6, decimal_places=2)

    @model_validator(mode="after")
    def require_at_least_one_measurement(self):
        if not any(getattr(self, field) is not None for field in self.model_fields):
            raise ValueError("Provide at least one vital-sign measurement.")
        if self.systolic_bp is not None and self.diastolic_bp is not None and self.systolic_bp <= self.diastolic_bp:
            raise ValueError("Systolic blood pressure must be greater than diastolic pressure.")
        return self


class VitalSignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    recorded_by: UUID | None
    temperature_c: Decimal | None
    pulse_bpm: int | None
    respiratory_rate: int | None
    systolic_bp: int | None
    diastolic_bp: int | None
    oxygen_saturation: Decimal | None
    weight_kg: Decimal | None
    height_cm: Decimal | None
    recorded_at: datetime


class DiagnosisCreate(BaseModel):
    code: str | None = Field(default=None, max_length=40)
    description: str = Field(min_length=2, max_length=5000)
    is_primary: bool = False

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Diagnosis description must contain at least 2 characters.")
        return value


class DiagnosisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    code: str | None
    description: str
    is_primary: bool
    recorded_by: UUID | None


class EmergencyEventCreate(BaseModel):
    patient_id: UUID | None = None
    encounter_id: UUID | None = None
    triage_level: TriageLevel
    chief_complaint: str = Field(min_length=2, max_length=5000)
    status: EmergencyStatus = "waiting"

    @field_validator("chief_complaint")
    @classmethod
    def normalize_complaint(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Chief complaint must contain at least 2 characters.")
        return value


class EmergencyTriageUpdate(BaseModel):
    triage_level: TriageLevel
    status: EmergencyStatus = "waiting"


class EmergencyEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID | None
    encounter_id: UUID | None
    triage_level: str
    chief_complaint: str
    status: str
    arrived_at: datetime
    triaged_by: UUID | None
