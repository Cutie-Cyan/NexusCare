from datetime import date, datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PatientCreate(BaseModel):
    medical_record_number: str = Field(min_length=2, max_length=40)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=180)
    emergency_contact_phone: str | None = Field(default=None, max_length=40)
    allergies: str | None = None
    notes: str | None = None

    @field_validator("first_name", "last_name", "medical_record_number")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("medical_record_number")
    @classmethod
    def validate_medical_record_number(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("Use only letters, numbers, hyphens, and underscores.")
        return value

    @field_validator("middle_name", "sex", "phone", "email", "address",
                     "emergency_contact_name", "emergency_contact_phone", "allergies", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_not_in_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=180)
    emergency_contact_phone: str | None = Field(default=None, max_length=40)
    allergies: str | None = None
    notes: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def required_text_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("This field cannot be blank.")
        return value.strip() if value is not None else None

    @field_validator("middle_name", "sex", "phone", "email", "address",
                     "emergency_contact_name", "emergency_contact_phone", "allergies", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_not_in_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_profile_id: UUID | None
    medical_record_number: str
    first_name: str
    middle_name: str | None
    last_name: str
    date_of_birth: date | None
    sex: str | None
    phone: str | None
    email: str | None
    address: str | None
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    allergies: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
