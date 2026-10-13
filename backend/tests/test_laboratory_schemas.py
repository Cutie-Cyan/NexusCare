from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.laboratory import (
    LaboratoryOrderCreate, LaboratoryOrderStatusUpdate, LaboratoryResultCreate,
    LaboratoryTestCreate,
)


def test_laboratory_test_normalizes_code_and_name():
    test = LaboratoryTestCreate(code=" cbc ", name=" Complete Blood Count ", base_fee="350.00")
    assert test.code == "CBC"
    assert test.name == "Complete Blood Count"
    assert test.base_fee == Decimal("350.00")


def test_laboratory_test_rejects_negative_fee():
    with pytest.raises(ValidationError):
        LaboratoryTestCreate(code="CBC", name="Complete Blood Count", base_fee="-1.00")


def test_laboratory_order_defaults_to_routine_priority():
    order = LaboratoryOrderCreate(encounter_id=uuid4(), test_id=uuid4())
    assert order.priority == "routine"


def test_laboratory_order_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        LaboratoryOrderCreate(encounter_id=uuid4(), test_id=uuid4(), priority="whenever")


def test_result_requires_text_or_structured_data():
    with pytest.raises(ValidationError):
        LaboratoryResultCreate()


def test_result_trims_text_and_accepts_structured_data():
    result = LaboratoryResultCreate(result_text="  Within reference range. ")
    assert result.result_text == "Within reference range."
    assert result.result_data is None
    structured = LaboratoryResultCreate(result_data={"hemoglobin": 13.2})
    assert structured.result_data == {"hemoglobin": 13.2}


def test_order_status_only_accepts_supported_lab_transitions():
    assert LaboratoryOrderStatusUpdate(status="collected").status == "collected"
    with pytest.raises(ValidationError):
        LaboratoryOrderStatusUpdate(status="completed")
