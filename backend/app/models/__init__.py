"""SQLAlchemy models for NexusCare Phase 2.

Keep clinical and financial records relational. Use Decimal/Numeric for money;
never represent financial amounts with floating-point values.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    auth_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("profile_id", "role_id", name="uq_user_roles_profile_role"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="CASCADE"))
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("roles.id", ondelete="RESTRICT"))
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Ward(Base, TimestampMixin):
    __tablename__ = "wards"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    ward_type: Mapped[str] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Bed(Base, TimestampMixin):
    __tablename__ = "beds"
    __table_args__ = (UniqueConstraint("ward_id", "bed_number", name="uq_beds_ward_number"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    ward_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("wards.id", ondelete="RESTRICT"))
    bed_number: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="available", server_default="available")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"
    __table_args__ = (
        Index("ix_patients_name_search", "last_name", "first_name"),
        UniqueConstraint("medical_record_number", name="uq_patients_mrn"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    medical_record_number: Mapped[str] = mapped_column(String(40))
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Admission(Base, TimestampMixin):
    __tablename__ = "admissions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    bed_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("beds.id", ondelete="RESTRICT"), nullable=True)
    admitted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    attending_doctor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    admission_type: Mapped[str] = mapped_column(String(40), default="general")
    status: Mapped[str] = mapped_column(String(30), default="admitted", index=True)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    discharged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discharge_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Encounter(Base, TimestampMixin):
    __tablename__ = "encounters"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    admission_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("admissions.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    clinician_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    encounter_type: Mapped[str] = mapped_column(String(40), default="consultation")
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VitalSign(Base):
    __tablename__ = "vital_signs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    encounter_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("encounters.id", ondelete="CASCADE"), index=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    temperature_c: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    pulse_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    systolic_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diastolic_bp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oxygen_saturation: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    encounter_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("encounters.id", ondelete="CASCADE"), index=True)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)


class LaboratoryTest(Base, TimestampMixin):
    __tablename__ = "laboratory_tests"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class LaboratoryOrder(Base, TimestampMixin):
    __tablename__ = "laboratory_orders"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    encounter_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    test_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("laboratory_tests.id", ondelete="RESTRICT"))
    ordered_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="ordered", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="routine")
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LaboratoryResult(Base):
    __tablename__ = "laboratory_results"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("laboratory_orders.id", ondelete="RESTRICT"), unique=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    entered_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="RESTRICT"))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Medicine(Base, TimestampMixin):
    __tablename__ = "medicines"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    strength: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dosage_form: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class MedicineBatch(Base):
    __tablename__ = "medicine_batches"
    __table_args__ = (UniqueConstraint("medicine_id", "batch_number", name="uq_medicine_batch_number"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    medicine_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("medicines.id", ondelete="RESTRICT"), index=True)
    batch_number: Mapped[str] = mapped_column(String(80))
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    encounter_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    prescribed_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="issued")
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    prescription_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True)
    medicine_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("medicines.id", ondelete="RESTRICT"))
    dose: Mapped[str] = mapped_column(String(120))
    route: Mapped[str | None] = mapped_column(String(80), nullable=True)
    frequency: Mapped[str] = mapped_column(String(120))
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)


class ServiceCatalog(Base, TimestampMixin):
    __tablename__ = "service_catalog"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(80))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Bill(Base, TimestampMixin):
    __tablename__ = "bills"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    patient_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True)
    bill_number: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    adjustments: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)


class BillItem(Base):
    __tablename__ = "bill_items"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    bill_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bills.id", ondelete="RESTRICT"), index=True)
    service_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("service_catalog.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    bill_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("bills.id", ondelete="RESTRICT"), index=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="posted")
    received_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    medicine_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("medicine_batches.id", ondelete="RESTRICT"), index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer)
    transaction_type: Mapped[str] = mapped_column(String(40))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    recipient_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="general")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    actor_profile_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
