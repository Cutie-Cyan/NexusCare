from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicineCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=180)
    strength: str | None = Field(default=None, max_length=80)
    dosage_form: str | None = Field(default=None, max_length=80)
    reorder_level: int = Field(default=0, ge=0)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Medicine code cannot be blank.")
        return value

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Medicine name cannot be blank.")
        return value


class MedicineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    strength: str | None
    dosage_form: str | None
    reorder_level: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MedicineBatchCreate(BaseModel):
    medicine_id: UUID
    batch_number: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=1000000)
    unit_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    selling_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    expires_on: date | None = None

    @field_validator("batch_number")
    @classmethod
    def normalize_batch(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Batch number cannot be blank.")
        return value


class MedicineBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    medicine_id: UUID
    batch_number: str
    quantity_on_hand: int
    unit_cost: Decimal
    selling_price: Decimal
    expires_on: date | None


class PrescriptionItemInput(BaseModel):
    medicine_id: UUID
    dose: str = Field(min_length=1, max_length=120)
    route: str | None = Field(default=None, max_length=80)
    frequency: str = Field(min_length=1, max_length=120)
    duration: str | None = Field(default=None, max_length=120)
    quantity: int = Field(gt=0, le=10000)
    instructions: str | None = Field(default=None, max_length=2000)

    @field_validator("dose", "frequency")
    @classmethod
    def normalize_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value


class PrescriptionCreate(BaseModel):
    encounter_id: UUID
    instructions: str | None = Field(default=None, max_length=5000)
    items: list[PrescriptionItemInput] = Field(min_length=1, max_length=50)


class PrescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    encounter_id: UUID
    prescribed_by: UUID
    status: str
    instructions: str | None
    created_at: datetime
    updated_at: datetime


class PrescriptionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prescription_id: UUID
    medicine_id: UUID
    dose: str
    route: str | None
    frequency: str
    duration: str | None
    quantity: int
    instructions: str | None


class DispenseCreate(BaseModel):
    medicine_batch_id: UUID
    quantity: int = Field(gt=0, le=10000)


class DispensingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prescription_item_id: UUID
    medicine_batch_id: UUID
    quantity: int
    dispensed_by: UUID
    dispensed_at: datetime


class InventoryStockRead(BaseModel):
    medicine_id: UUID
    medicine_name: str
    reorder_level: int
    total_quantity: int
    batches: list[MedicineBatchRead]
    stock_status: Literal["out_of_stock", "low_stock", "in_stock"]
