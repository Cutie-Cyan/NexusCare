from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcurementItemInput(BaseModel):
    inventory_item_id: UUID
    requested_quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)


class ProcurementRequestCreate(BaseModel):
    request_number: str = Field(min_length=3, max_length=50)
    supplier_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=3000)
    items: list[ProcurementItemInput] = Field(min_length=1, max_length=100)

    @field_validator("request_number")
    @classmethod
    def normalize_request_number(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Request number cannot be blank.")
        return value

    @field_validator("items")
    @classmethod
    def unique_inventory_items(cls, value: list[ProcurementItemInput]) -> list[ProcurementItemInput]:
        item_ids = [item.inventory_item_id for item in value]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("A procurement request cannot contain the same inventory item twice.")
        return value


class ProcurementRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_number: str
    supplier_id: UUID | None
    requested_by: UUID
    approved_by: UUID | None
    status: str
    notes: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProcurementItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_id: UUID
    inventory_item_id: UUID
    requested_quantity: Decimal
    received_quantity: Decimal
    unit_cost: Decimal
    notes: str | None


class ReceivingRecordCreate(BaseModel):
    quantity_received: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    supplier_reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class ReceivingRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    procurement_item_id: UUID
    quantity_received: Decimal
    received_by: UUID
    supplier_reference: str | None
    notes: str | None
    received_at: datetime


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=3000)

    @field_validator("code")
    @classmethod
    def normalize_department_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Department code cannot be blank.")
        return value

    @field_validator("name")
    @classmethod
    def normalize_department_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Department name cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def normalize_department_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SupplierCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=180)
    contact_name: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=3000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InventoryItemCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=180)
    category: str = Field(min_length=2, max_length=80)
    unit: str = Field(default="piece", min_length=1, max_length=40)
    reorder_level: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=3)
    unit_cost: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    supplier_id: UUID | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    category: str
    unit: str
    quantity_on_hand: Decimal
    reorder_level: Decimal
    unit_cost: Decimal
    supplier_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InventoryMovementCreate(BaseModel):
    quantity_delta: Decimal = Field(max_digits=12, decimal_places=3)
    transaction_type: Literal["receipt", "issue", "adjustment"]
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("quantity_delta")
    @classmethod
    def reject_zero_delta(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Inventory movement must change stock by a nonzero quantity.")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class InventoryItemTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_id: UUID
    quantity_delta: Decimal
    transaction_type: str
    reference_id: UUID | None
    recorded_by: UUID | None
    notes: str | None
    created_at: datetime


class DoctorScheduleCreate(BaseModel):
    doctor_id: UUID
    department_id: UUID | None = None
    weekday: int = Field(ge=0, le=6)
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    is_active: bool = True

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, value: str, info):
        start = info.data.get("start_time")
        if start and value <= start:
            raise ValueError("Schedule end time must be after start time.")
        return value


class DoctorScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    doctor_id: UUID
    department_id: UUID | None
    weekday: int
    start_time: str
    end_time: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AppointmentCreate(BaseModel):
    patient_id: UUID | None = None
    department_id: UUID | None = None
    clinician_id: UUID | None = None
    scheduled_at: datetime
    reason: str | None = Field(default=None, max_length=3000)

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Appointment datetime must include a timezone.")
        return value


class AppointmentStatusUpdate(BaseModel):
    status: Literal["scheduled", "confirmed", "checked_in", "completed", "cancelled", "no_show"]


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    department_id: UUID | None
    clinician_id: UUID | None
    scheduled_at: datetime
    status: str
    reason: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class OnlineConsultationCreate(BaseModel):
    meeting_url: str | None = Field(default=None, max_length=2000)


class OnlineConsultationUpdate(BaseModel):
    status: Literal["scheduled", "in_progress", "completed", "cancelled"]
    meeting_url: str | None = Field(default=None, max_length=2000)


class OnlineConsultationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    appointment_id: UUID
    meeting_url: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None


class NotificationCreate(BaseModel):
    recipient_profile_id: UUID
    title: str = Field(min_length=2, max_length=180)
    message: str = Field(min_length=2, max_length=5000)
    category: str = Field(default="general", min_length=2, max_length=60)


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recipient_profile_id: UUID
    title: str
    message: str
    category: str
    read_at: datetime | None
    created_at: datetime


class SystemSettingWrite(BaseModel):
    setting_value: dict
    description: str | None = Field(default=None, max_length=3000)


class SystemSettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    setting_key: str
    setting_value: dict
    description: str | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=40)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=3000)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_update_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name")
    @classmethod
    def normalize_update_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("description")
    @classmethod
    def normalize_update_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None
