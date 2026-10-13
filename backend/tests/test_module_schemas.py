from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.billing import BillCreate, BillItemInput, PaymentCreate, PaymentReversal
from app.schemas.operations import AppointmentCreate, InventoryMovementCreate, SystemSettingWrite
from app.schemas.pharmacy import (
    DispenseCreate, MedicineBatchCreate, MedicineCreate, PrescriptionCreate,
    PrescriptionItemInput,
)


def test_medicine_code_is_normalized_and_reorder_level_is_nonnegative():
    medicine = MedicineCreate(code=" par-500 ", name="Paracetamol", reorder_level=10)
    assert medicine.code == "PAR-500"
    assert medicine.reorder_level == 10
    with pytest.raises(ValidationError):
        MedicineCreate(code="PAR-500", name="Paracetamol", reorder_level=-1)


def test_medicine_batch_requires_positive_quantity_and_nonnegative_prices():
    batch = MedicineBatchCreate(
        medicine_id=uuid4(), batch_number="B-001", quantity=25,
        unit_cost="2.50", selling_price="4.00",
    )
    assert batch.quantity == 25
    with pytest.raises(ValidationError):
        MedicineBatchCreate(
            medicine_id=uuid4(), batch_number="B-002", quantity=0,
            unit_cost="2.50", selling_price="4.00",
        )


def test_prescription_requires_at_least_one_valid_item():
    item = PrescriptionItemInput(
        medicine_id=uuid4(), dose="1 tablet", frequency="twice daily", quantity=6,
    )
    prescription = PrescriptionCreate(encounter_id=uuid4(), items=[item])
    assert len(prescription.items) == 1
    with pytest.raises(ValidationError):
        PrescriptionCreate(encounter_id=uuid4(), items=[])


def test_dispensing_quantity_must_be_positive():
    assert DispenseCreate(medicine_batch_id=uuid4(), quantity=2).quantity == 2
    with pytest.raises(ValidationError):
        DispenseCreate(medicine_batch_id=uuid4(), quantity=0)


def test_bill_total_uses_decimal_and_rejects_empty_items():
    bill = BillCreate(
        patient_id=uuid4(), bill_number="BILL-001",
        items=[BillItemInput(description="Consultation", quantity=2, unit_price=Decimal("150.00"))],
    )
    assert bill.items[0].unit_price == Decimal("150.00")
    with pytest.raises(ValidationError):
        BillCreate(patient_id=uuid4(), bill_number="BILL-002", items=[])


def test_payment_requires_positive_decimal_amount():
    assert PaymentCreate(amount="50.00", payment_method="cash").amount == Decimal("50.00")
    with pytest.raises(ValidationError):
        PaymentCreate(amount="0", payment_method="cash")


def test_payment_reversal_requires_reason():
    assert PaymentReversal(reason="Duplicate payment").reason == "Duplicate payment"
    with pytest.raises(ValidationError):
        PaymentReversal(reason="  ")


def test_inventory_movements_require_nonzero_delta():
    assert InventoryMovementCreate(quantity_delta="3.000", transaction_type="receipt").quantity_delta == Decimal("3.000")
    with pytest.raises(ValidationError):
        InventoryMovementCreate(quantity_delta="0", transaction_type="receipt")


def test_appointment_datetime_requires_timezone():
    appointment = AppointmentCreate(
        patient_id=uuid4(), scheduled_at=datetime(2027, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    assert appointment.scheduled_at.tzinfo is not None
    with pytest.raises(ValidationError):
        AppointmentCreate(patient_id=uuid4(), scheduled_at=datetime(2027, 1, 1, 10, 0))


def test_system_setting_value_is_structured():
    setting = SystemSettingWrite(setting_value={"maintenance_mode": False})
    assert setting.setting_value["maintenance_mode"] is False
