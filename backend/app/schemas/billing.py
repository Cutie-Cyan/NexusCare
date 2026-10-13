from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


PaymentMethod = Literal["cash", "card", "bank_transfer", "ewallet", "insurance", "other"]


class BillItemInput(BaseModel):
    description: str = Field(min_length=2, max_length=240)
    quantity: int = Field(gt=0, le=100000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    service_id: UUID | None = None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be blank.")
        return value


class BillCreate(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    bill_number: str = Field(min_length=3, max_length=50)
    adjustments: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    items: list[BillItemInput] = Field(min_length=1, max_length=100)

    @field_validator("bill_number")
    @classmethod
    def normalize_number(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Bill number cannot be blank.")
        return value


class BillItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bill_id: UUID
    service_id: UUID | None
    description: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    bill_number: str
    status: str
    subtotal: Decimal
    adjustments: Decimal
    total: Decimal
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    bill_id: UUID
    receipt_number: str
    idempotency_key: str
    amount: Decimal
    payment_method: str
    status: str
    received_by: UUID | None
    received_at: datetime
    reversed_at: datetime | None
    reversal_reason: str | None


class PaymentReversal(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("A reversal reason is required.")
        return value


class BillBalanceRead(BaseModel):
    bill_id: UUID
    bill_number: str
    total: Decimal
    paid: Decimal
    balance: Decimal
    status: str
