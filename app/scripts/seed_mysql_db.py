import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.db.sql.models.tables import PatientRow, StaffRow

from passlib.hash import bcrypt


DATABASE_URL = "mysql+pymysql://opd_user:opd_password@mysql:3306/opd_vertex"

def seed():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try: 
        print("Seeding database...")
        existing_patient = db.query(PatientRow).filter_by(email="jane@example.com").first()
        if not existing_patient:
            hashed_pw = bcrypt.hash("password")
            new_patient = PatientRow(
                first_name="Jane",
                last_name="Smith",
                email="jane@example.com",
                date_of_birth="1990-01-01",
                password_hash=hashed_pw,
                role="patient",
                is_active=True
            )
            db.add(new_patient)

        existing_staff = db.query(StaffRow).filter_by(email="john@example.com").first()
        if not existing_staff:
            hashed_pw = bcrypt.hash("password")
            new_doctor = StaffRow(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                password_hash=hashed_pw,
                role="doctor",
                is_active=True,
                specialization="Diagnostics",
                license_number="DOC123456"
            )
            db.add(new_doctor)

        existing_staff = db.query(StaffRow).filter_by(email="bob@example.com").first()
        if not existing_staff:
            hashed_pw = bcrypt.hash("password")
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