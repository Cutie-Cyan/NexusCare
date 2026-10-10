"""Seed reference data and fictional patients for local/demo use only.

Run from backend/: uv run python scripts/seed_demo.py
Optional Supabase demo doctors:
  SEED_DOCTOR_PASSWORD='a-strong-demo-only-password' uv run python scripts/seed_demo.py --create-auth-users

The optional Auth seeding requires SUPABASE_SECRET_KEY and creates five confirmed,
fictional development doctor accounts. Never use these demo accounts in production.
"""
import argparse
import os
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from supabase import create_client

from app.core.config import get_settings
from app.db.session import get_engine
from app.models import (
    Department, LaboratoryTest, Medicine, Patient, Profile, Role,
    ServiceCatalog, UserRole,
)

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
DOCTORS = [
    ("nexuscare.doctor01@example.test", "Dr. Andrea Reyes"),
    ("nexuscare.doctor02@example.test", "Dr. Miguel Santos"),
    ("nexuscare.doctor03@example.test", "Dr. Bianca Cruz"),
    ("nexuscare.doctor04@example.test", "Dr. Rafael Garcia"),
    ("nexuscare.doctor05@example.test", "Dr. Elena Mendoza"),
]


def seed_reference_data(session: Session) -> dict[str, Department]:
    for code, name in ROLES:
        if session.scalar(select(Role).where(Role.code == code)) is None:
            session.add(Role(code=code, name=name))
    session.flush()

    department_map: dict[str, Department] = {}
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
    return department_map


def seed_doctor_auth_users(session: Session, department: Department) -> None:
    settings = get_settings()
    password = os.getenv("SEED_DOCTOR_PASSWORD", "")
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError(
            "Set SUPABASE_URL and server-only SUPABASE_SECRET_KEY before --create-auth-users."
        )
    if len(password) < 12:
        raise RuntimeError("Set SEED_DOCTOR_PASSWORD to a demo-only password of at least 12 characters.")

    admin = create_client(settings.supabase_url, settings.supabase_secret_key)
    listed = admin.auth.admin.list_users()
    users = getattr(listed, "users", listed)
    auth_users = {str(getattr(user, "email", "")).lower(): user for user in users}
    doctor_role = session.scalar(select(Role).where(Role.code == "doctor"))
    if doctor_role is None:
        raise RuntimeError("Doctor role was not seeded.")

    for email, full_name in DOCTORS:
        profile = session.scalar(select(Profile).where(Profile.email == email))
        auth_user = auth_users.get(email.lower())
        if auth_user is None:
            response = admin.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": full_name},
            })
            auth_user = getattr(response, "user", None)
            if auth_user is None:
                raise RuntimeError(f"Supabase Auth did not return the user for {email}.")
            auth_users[email.lower()] = auth_user

        if profile is None:
            profile = Profile(
                auth_user_id=UUID(str(auth_user.id)),
                full_name=full_name,
                email=email,
                department_id=department.id,
                is_active=True,
            )
            session.add(profile)
            session.flush()

        assignment = session.scalar(
            select(UserRole).where(
                UserRole.profile_id == profile.id,
                UserRole.role_id == doctor_role.id,
            )
        )
        if assignment is None:
            session.add(UserRole(profile_id=profile.id, role_id=doctor_role.id))
        session.flush()

    session.commit()
    print("Five fictional doctor accounts and their doctor roles are ready.")
    print("Demo email addresses and passwords must remain development-only.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed NexusCare fictional demo data.")
    parser.add_argument(
        "--create-auth-users",
        action="store_true",
        help="Create/link five demo doctor accounts using the Supabase Auth admin API.",
    )
    args = parser.parse_args()

    engine = get_engine()
    with Session(engine) as session:
        departments = seed_reference_data(session)
        if args.create_auth_users:
            seed_doctor_auth_users(session, departments["GEN"])
    print("Demo reference data and 20 fictional patient records are ready.")
