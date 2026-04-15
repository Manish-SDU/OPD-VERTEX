from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.infrastructure.db.sql.connection import get_mysql_url
from app.infrastructure.db.sql.models.tables import PatientRow, StaffRow


def seed():
    engine = create_engine(get_mysql_url())
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        print("Seeding database...")
        existing_patient = (
            db.query(PatientRow).filter_by(email="jane@example.com").first()
        )
        if not existing_patient:
            hashed_pw = hash_password("password")
            new_patient = PatientRow(
                first_name="Jane",
                last_name="Smith",
                email="jane@example.com",
                date_of_birth=date(1990, 1, 1),
                password_hash=hashed_pw,
                role="patient",
                is_active=True,
            )
            db.add(new_patient)

        existing_staff = db.query(StaffRow).filter_by(email="john@example.com").first()
        if not existing_staff:
            hashed_pw = hash_password("password")
            new_doctor = StaffRow(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password_hash=hashed_pw,
                role="doctor",
                is_active=True,
                specialization="Diagnostics",
                license_number="DOC123456",
            )
            db.add(new_doctor)

        existing_staff = db.query(StaffRow).filter_by(email="bob@example.com").first()
        if not existing_staff:
            hashed_pw = hash_password("password")
            new_admin = StaffRow(
                first_name="Bob",
                last_name="Jones",
                email="bob@example.com",
                password_hash=hashed_pw,
                role="admin",
                is_active=True,
            )
            db.add(new_admin)
        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding: {e} ")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
