"""Seed reference data and fictional patients for local/demo use only.

Run from backend/: uv run python scripts/seed_demo.py
Requires DATABASE_URL. This script does not create Supabase Auth accounts or passwords.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models import Base, Department, LaboratoryTest, Medicine, Patient, Role, ServiceCatalog, Ward

ROLES = [
    ("administrator", "Administrator"),
    ("information_officer", "Information Officer / Receptionist"),
    ("doctor", "Doctor"),
    ("nurse", "Nurse"),
    ("cashier", "Cashier"),
    ("laboratory_staff", "Laboratory Staff"),
    ("pharmacy_staff", "Pharmacy Staff"),
    ("patient", "Patient"),
]
DEPARTMENTS = [
    ("ER", "Emergency Room"), ("GEN", "General Medicine"), ("PED", "Pediatrics"),
    ("LAB", "Laboratory"), ("PHARM", "Pharmacy"), ("NURS", "Nursing"),
    ("CASH", "Cashier"), ("ADMIN", "Administration"),
]
PATIENT_NAMES = [
    ("Ava", "Santos"), ("Noah", "Reyes"), ("Mia", "Cruz"), ("Liam", "Garcia"),
    ("Isla", "Mendoza"), ("Ethan", "Ramos"), ("Zoe", "Flores"), ("Lucas", "Torres"),
    ("Ella", "Castillo"), ("Mateo", "Rivera"), ("Luna", "Aquino"), ("Gabriel", "Navarro"),
    ("Chloe", "Villanueva"), ("Daniel", "Bautista"), ("Nina", "Domingo"),
    ("Adrian", "Fernandez"), ("Sofia", "Mercado"), ("Caleb", "Dizon"),
    ("Leah", "Salazar"), ("Miguel", "Valdez"),
]


def seed(session: Session) -> None:
    for code, name in ROLES:
        if session.scalar(select(Role).where(Role.code == code)) is None:
            session.add(Role(code=code, name=name))
    session.flush()

    department_map = {}
    for code, name in DEPARTMENTS:
        department = session.scalar(select(Department).where(Department.code == code))
        if department is None:
            department = Department(code=code, name=name)
            session.add(department)
            session.flush()
        department_map[code] = department

    for code, name, category, price in [
        ("CONSULT", "General Consultation", "professional_fee", "500.00"),
        ("CBC", "Complete Blood Count", "laboratory", "350.00"),
        ("XRAY", "Chest X-Ray", "imaging", "800.00"),
        ("ROOM", "Ward Accommodation", "accommodation", "1200.00"),
    ]:
        if session.scalar(select(ServiceCatalog).where(ServiceCatalog.code == code)) is None:
            session.add(ServiceCatalog(code=code, name=name, category=category, price=Decimal(price)))

    for code, name, fee in [
        ("CBC", "Complete Blood Count", "350.00"),
        ("URINALYSIS", "Urinalysis", "180.00"),
        ("FBS", "Fasting Blood Sugar", "200.00"),
    ]:
        if session.scalar(select(LaboratoryTest).where(LaboratoryTest.code == code)) is None:
            session.add(LaboratoryTest(code=code, name=name, base_fee=Decimal(fee)))

    for code, name, strength, form in [
        ("MED-PARA-500", "Paracetamol", "500 mg", "tablet"),
        ("MED-AMOX-500", "Amoxicillin", "500 mg", "capsule"),
        ("MED-ORS", "Oral Rehydration Salts", None, "sachet"),
    ]:
        if session.scalar(select(Medicine).where(Medicine.code == code)) is None:
            session.add(Medicine(code=code, name=name, strength=strength, dosage_form=form))

    for index, (first, last) in enumerate(PATIENT_NAMES, start=1):
        mrn = f"DEMO-{index:05d}"
        if session.scalar(select(Patient).where(Patient.medical_record_number == mrn)) is None:
            session.add(
                Patient(
                    medical_record_number=mrn,
                    first_name=first,
                    last_name=last,
                    date_of_birth=date(1990 + index % 25, (index % 12) + 1, (index % 27) + 1),
                    sex="not_specified",
                    notes="Fictional seed record. Do not use as real patient information.",
                )
            )
    session.commit()


if __name__ == "__main__":
    engine = get_engine()
    with Session(engine) as session:
        seed(session)
    print("Demo reference data and 20 fictional patient records are ready.")
