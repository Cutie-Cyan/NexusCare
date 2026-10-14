"""Seed reference data and fictional patients for local/demo use only.

Run from backend/: uv run python scripts/seed_demo.py
Optional Supabase demo doctors:
  SEED_DOCTOR_PASSWORD='a-strong-demo-only-password' uv run python scripts/seed_demo.py --create-auth-users

The optional Auth seeding requires SUPABASE_SECRET_KEY and creates five confirmed,
fictional development doctor accounts. Never use these demo accounts in production.
"""
import argparse
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from supabase import create_client

from app.core.config import get_settings
from app.db.session import get_engine
from app.models import (
    Bed, Department, InventoryItem, InventoryItemTransaction, LaboratoryTest,
    Medicine, Patient, Profile, Role, ServiceCatalog, Supplier, UserRole, Ward,
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
    ("CASH", "Cashier"), ("ADMIN", "Administration"), ("OBGYN", "Obstetrics & Delivery"),
]
PATIENT_DEMO_RECORDS = [
    {"first_name": "Sofia", "middle_name": "Marie", "last_name": "Santos", "date_of_birth": date.fromisoformat("1998-04-12"), "sex": "female", "phone": "0900-000-0001", "email": "sofia.santos@example.test", "address": "Unit 2, 18 Sampaguita Street, Brgy. San Pedro, Puerto Princesa City, Palawan", "emergency_contact_name": "Elena Santos", "emergency_contact_phone": "0900-000-0101", "allergies": "No known drug allergies reported", "notes": "Routine outpatient demo profile; fictional data for system demonstration only."},
    {"first_name": "Gabriel", "middle_name": "Luis", "last_name": "Reyes", "date_of_birth": date.fromisoformat("1985-11-03"), "sex": "male", "phone": "0900-000-0002", "email": "gabriel.reyes@example.test", "address": "42 Mabini Street, Brgy. Tiniguiban, Puerto Princesa City, Palawan", "emergency_contact_name": "Teresa Reyes", "emergency_contact_phone": "0900-000-0102", "allergies": "Penicillin (reported)", "notes": "Fictional demo patient; verify all information before any clinical use."},
    {"first_name": "Isabella", "middle_name": "Grace", "last_name": "Cruz", "date_of_birth": date.fromisoformat("2001-02-19"), "sex": "female", "phone": "0900-000-0003", "email": "isabella.cruz@example.test", "address": "15 Rizal Avenue, Brgy. Model, Puerto Princesa City, Palawan", "emergency_contact_name": "Maricel Cruz", "emergency_contact_phone": "0900-000-0103", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Miguel", "middle_name": "Andres", "last_name": "Garcia", "date_of_birth": date.fromisoformat("1979-07-28"), "sex": "male", "phone": "0900-000-0004", "email": "miguel.garcia@example.test", "address": "8 Narra Road, Brgy. San Miguel, Puerto Princesa City, Palawan", "emergency_contact_name": "Roberto Garcia", "emergency_contact_phone": "0900-000-0104", "allergies": "Shellfish (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Camille", "middle_name": "Anne", "last_name": "Mendoza", "date_of_birth": date.fromisoformat("1994-09-14"), "sex": "female", "phone": "0900-000-0005", "email": "camille.mendoza@example.test", "address": "23 Acacia Street, Brgy. Bancao-Bancao, Puerto Princesa City, Palawan", "emergency_contact_name": "Lourdes Mendoza", "emergency_contact_phone": "0900-000-0105", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Joshua", "middle_name": "Miguel", "last_name": "Ramos", "date_of_birth": date.fromisoformat("1990-12-06"), "sex": "male", "phone": "0900-000-0006", "email": "joshua.ramos@example.test", "address": "Block 4 Lot 7, Brgy. Sta. Monica, Puerto Princesa City, Palawan", "emergency_contact_name": "Ramon Ramos", "emergency_contact_phone": "0900-000-0106", "allergies": "Latex (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Angela", "middle_name": "Mae", "last_name": "Flores", "date_of_birth": date.fromisoformat("2003-05-22"), "sex": "female", "phone": "0900-000-0007", "email": "angela.flores@example.test", "address": "17 Orchid Street, Brgy. Irawan, Puerto Princesa City, Palawan", "emergency_contact_name": "Marites Flores", "emergency_contact_phone": "0900-000-0107", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Nathaniel", "middle_name": "Jose", "last_name": "Torres", "date_of_birth": date.fromisoformat("1968-01-30"), "sex": "male", "phone": "0900-000-0008", "email": "nathaniel.torres@example.test", "address": "31 Bonifacio Street, Brgy. San Jose, Puerto Princesa City, Palawan", "emergency_contact_name": "Rogelio Torres", "emergency_contact_phone": "0900-000-0108", "allergies": "Aspirin (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Patricia", "middle_name": "Joy", "last_name": "Castillo", "date_of_birth": date.fromisoformat("1988-03-09"), "sex": "female", "phone": "0900-000-0009", "email": "patricia.castillo@example.test", "address": "5 Mabuhay Lane, Brgy. Sicsican, Puerto Princesa City, Palawan", "emergency_contact_name": "Cecilia Castillo", "emergency_contact_phone": "0900-000-0109", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Enzo", "middle_name": "Rafael", "last_name": "Rivera", "date_of_birth": date.fromisoformat("2012-08-17"), "sex": "male", "phone": "0900-000-0010", "email": "enzo.rivera@example.test", "address": "House 12, Brgy. San Manuel, Puerto Princesa City, Palawan", "emergency_contact_name": "Monica Rivera", "emergency_contact_phone": "0900-000-0110", "allergies": "Peanuts (reported)", "notes": "Fictional pediatric demo record; contact is a parent/guardian."},
    {"first_name": "Andrea", "middle_name": "Nicole", "last_name": "Aquino", "date_of_birth": date.fromisoformat("1996-06-25"), "sex": "female", "phone": "0900-000-0011", "email": "andrea.aquino@example.test", "address": "44 Rizal Street, Brgy. Tagumpay, Puerto Princesa City, Palawan", "emergency_contact_name": "Rina Aquino", "emergency_contact_phone": "0900-000-0111", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Daniel", "middle_name": "Paolo", "last_name": "Navarro", "date_of_birth": date.fromisoformat("1974-10-11"), "sex": "male", "phone": "0900-000-0012", "email": "daniel.navarro@example.test", "address": "9 Malvar Street, Brgy. Mandaragat, Puerto Princesa City, Palawan", "emergency_contact_name": "Lilia Navarro", "emergency_contact_phone": "0900-000-0112", "allergies": "Ibuprofen (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Chloe", "middle_name": "Beatriz", "last_name": "Villanueva", "date_of_birth": date.fromisoformat("2000-01-16"), "sex": "female", "phone": "0900-000-0013", "email": "chloe.villanueva@example.test", "address": "26 Narra Street, Brgy. Sta. Lourdes, Puerto Princesa City, Palawan", "emergency_contact_name": "Teresa Villanueva", "emergency_contact_phone": "0900-000-0113", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Marco", "middle_name": "Antonio", "last_name": "Bautista", "date_of_birth": date.fromisoformat("1982-04-04"), "sex": "male", "phone": "0900-000-0014", "email": "marco.bautista@example.test", "address": "10 Bonifacio Extension, Brgy. San Pedro, Puerto Princesa City, Palawan", "emergency_contact_name": "Rogelio Bautista", "emergency_contact_phone": "0900-000-0114", "allergies": "Adhesive tape (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Nicole", "middle_name": "Therese", "last_name": "Domingo", "date_of_birth": date.fromisoformat("1992-11-27"), "sex": "female", "phone": "0900-000-0015", "email": "nicole.domingo@example.test", "address": "7 Mabini Street, Brgy. Tiniguiban, Puerto Princesa City, Palawan", "emergency_contact_name": "Rosa Domingo", "emergency_contact_phone": "0900-000-0115", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Adrian", "middle_name": "Felix", "last_name": "Fernandez", "date_of_birth": date.fromisoformat("2005-07-02"), "sex": "male", "phone": "0900-000-0016", "email": "adrian.fernandez@example.test", "address": "16 Acacia Road, Brgy. San Miguel, Puerto Princesa City, Palawan", "emergency_contact_name": "Maria Fernandez", "emergency_contact_phone": "0900-000-0116", "allergies": "Eggs (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Samantha", "middle_name": "Claire", "last_name": "Mercado", "date_of_birth": date.fromisoformat("1986-02-08"), "sex": "female", "phone": "0900-000-0017", "email": "samantha.mercado@example.test", "address": "3 Orchid Street, Brgy. Bancao-Bancao, Puerto Princesa City, Palawan", "emergency_contact_name": "Liza Mercado", "emergency_contact_phone": "0900-000-0117", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Caleb", "middle_name": "Martin", "last_name": "Dizon", "date_of_birth": date.fromisoformat("1999-09-20"), "sex": "male", "phone": "0900-000-0018", "email": "caleb.dizon@example.test", "address": "29 Rizal Avenue, Brgy. Model, Puerto Princesa City, Palawan", "emergency_contact_name": "Antonio Dizon", "emergency_contact_phone": "0900-000-0118", "allergies": "Sulfa medicines (reported)", "notes": "Fictional demo patient record."},
    {"first_name": "Leah", "middle_name": "Patricia", "last_name": "Salazar", "date_of_birth": date.fromisoformat("1971-12-15"), "sex": "female", "phone": "0900-000-0019", "email": "leah.salazar@example.test", "address": "11 Narra Road, Brgy. San Jose, Puerto Princesa City, Palawan", "emergency_contact_name": "Evelyn Salazar", "emergency_contact_phone": "0900-000-0119", "allergies": "No known drug allergies reported", "notes": "Fictional demo patient record."},
    {"first_name": "Rafael", "middle_name": "Gabriel", "last_name": "Valdez", "date_of_birth": date.fromisoformat("1991-05-31"), "sex": "male", "phone": "0900-000-0020", "email": "rafael.valdez@example.test", "address": "6 Sampaguita Street, Brgy. Irawan, Puerto Princesa City, Palawan", "emergency_contact_name": "Julio Valdez", "emergency_contact_phone": "0900-000-0120", "allergies": "Contrast media (reported)", "notes": "Fictional demo patient record."},
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

    # Fictional ward and bed capacity for local development. Seed is idempotent.
    for ward_code, ward_name, ward_type, department_code, bed_count in [
        ("GEN-WARD", "General Ward", "inpatient", "NURS", 10),
        ("ER-WARD", "Emergency Observation", "observation", "ER", 5),
        ("PED-WARD", "Pediatric Ward", "pediatric", "PED", 5),
        ("FEMALE-WARD", "Female Ward", "inpatient", "NURS", 5),
        ("DELIVERY", "Delivery Room", "maternity", "OBGYN", 5),
    ]:
        ward = session.scalar(select(Ward).where(Ward.code == ward_code))
        if ward is None:
            ward = Ward(
                code=ward_code,
                name=ward_name,
                ward_type=ward_type,
                department_id=department_map[department_code].id,
            )
            session.add(ward)
            session.flush()
        for bed_number in range(1, bed_count + 1):
            number = f"{bed_number:02d}"
            if session.scalar(select(Bed.id).where(
                Bed.ward_id == ward.id, Bed.bed_number == number
            )) is None:
                session.add(Bed(ward_id=ward.id, bed_number=number, status="available"))

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


    suppliers = {}
    for code, name in [
        ("SUP-MED", "Fictional Medical Supply Co."),
        ("SUP-GEN", "Fictional General Hospital Supplies"),
    ]:
        supplier = session.scalar(select(Supplier).where(Supplier.code == code))
        if supplier is None:
            supplier = Supplier(code=code, name=name, is_active=True)
            session.add(supplier)
            session.flush()
        suppliers[code] = supplier

    for code, name, category, unit, reorder_level, unit_cost, supplier_code, opening_qty in [
        ("SUP-GLOVE", "Examination Gloves", "medical_supply", "box", "10.000", "120.00", "SUP-MED", "30.000"),
        ("SUP-MASK", "Surgical Masks", "medical_supply", "box", "8.000", "75.00", "SUP-MED", "25.000"),
        ("SUP-SHEET", "Patient Bed Sheets", "linen", "piece", "5.000", "180.00", "SUP-GEN", "15.000"),
    ]:
        item = session.scalar(select(InventoryItem).where(InventoryItem.code == code))
        if item is None:
            item = InventoryItem(
                code=code, name=name, category=category, unit=unit,
                quantity_on_hand=Decimal("0"), reorder_level=Decimal(reorder_level),
                unit_cost=Decimal(unit_cost), supplier_id=suppliers[supplier_code].id,
                is_active=True,
            )
            session.add(item)
            session.flush()
        opening_record = session.scalar(select(InventoryItemTransaction.id).where(
            InventoryItemTransaction.item_id == item.id,
            InventoryItemTransaction.notes == "Fictional seed opening stock",
        ))
        if opening_record is None:
            quantity = Decimal(opening_qty)
            item.quantity_on_hand += quantity
            session.add(InventoryItemTransaction(
                item_id=item.id, quantity_delta=quantity, transaction_type="receipt",
                notes="Fictional seed opening stock",
            ))

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
    password = settings.seed_doctor_password
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
