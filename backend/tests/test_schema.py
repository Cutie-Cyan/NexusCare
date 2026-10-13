from sqlalchemy import Numeric

from app.models import Base


def test_core_hospital_tables_are_registered():
    expected = {
        "roles",
        "profiles",
        "user_roles",
        "departments",
        "wards",
        "beds",
        "patients",
        "admissions",
        "encounters",
        "vital_signs",
        "diagnoses",
        "consultations",
        "nursing_notes",
        "laboratory_orders",
        "laboratory_results",
        "prescriptions",
        "pharmacy_dispensing",
        "inventory_items",
        "inventory_transactions",
        "bills",
        "bill_items",
        "payments",
        "payment_allocations",
        "receipts",
        "appointments",
        "notifications",
        "audit_logs",
    }
    assert expected.issubset(Base.metadata.tables.keys())


def test_money_columns_use_fixed_precision_numeric():
    amount = Base.metadata.tables["payments"].columns["amount"].type
    assert isinstance(amount, Numeric)
    assert amount.precision == 12
    assert amount.scale == 2


def test_patient_records_can_be_linked_to_auth_profiles():
    patients = Base.metadata.tables["patients"]
    assert "patient_profile_id" in patients.columns
    assert patients.columns["patient_profile_id"].unique is True


def test_admission_and_ward_tables_have_required_foreign_keys():
    admissions = Base.metadata.tables["admissions"]
    beds = Base.metadata.tables["beds"]
    assert admissions.columns["patient_id"].nullable is False
    assert "patients.id" in {str(fk.column) for fk in admissions.columns["patient_id"].foreign_keys}
    assert "wards.id" in {str(fk.column) for fk in beds.columns["ward_id"].foreign_keys}


def test_admission_bed_assignment_is_optional_for_emergency_overflow():
    admissions = Base.metadata.tables["admissions"]
    assert admissions.columns["bed_id"].nullable is True
