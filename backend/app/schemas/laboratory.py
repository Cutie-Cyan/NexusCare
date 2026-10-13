from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LabPriority = Literal["routine", "urgent", "stat"]
LabOrderStatus = Literal["ordered", "collected", "in_progress", "completed", "cancelled"]


class LaboratoryTestCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    base_fee: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) < 2:
            raise ValueError("Test code must contain at least 2 characters.")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Test name must contain at least 2 characters.")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class LaboratoryTestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None
    base_fee: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LaboratoryOrderCreate(BaseModel):
    encounter_id: UUID
    test_id: UUID
    priority: LabPriority = "routine"
    clinical_notes: str | None = Field(default=None, max_length=5000)

    @field_validator("clinical_notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class LaboratoryOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    test_id: UUID
    ordered_by: UUID
    status: str
    priority: str
    clinical_notes: str | None
    ordered_at: datetime
    created_at: datetime
    updated_at: datetime


class LaboratoryOrderStatusUpdate(BaseModel):
    status: Literal["collected", "in_progress", "cancelled"]


class LaboratoryResultCreate(BaseModel):
    result_text: str | None = Field(default=None, min_length=1, max_length=20000)
    result_data: dict | None = None

    @field_validator("result_text")
    @classmethod
    def normalize_result_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def require_result_payload(self):
        if not self.result_text and not self.result_data:
            raise ValueError("Provide result text or structured result data.")
        return self


class LaboratoryResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    order_id: UUID
    result_text: str | None
    result_data: dict | None
    entered_by: UUID
    verified_by: UUID | None
    status: str
    entered_at: datetime
    released_at: datetime | None
