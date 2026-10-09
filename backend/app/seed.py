"""Populates the database with demo clinic data.

Usage:
    python -m app.seed          # add demo data if the tables are empty
    python -m app.seed --reset  # wipe appointments/patients/doctors first
"""

import argparse
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.database import Base, SessionLocal, engine
from app.models import Appointment, AppointmentStatus, Doctor, Patient

DOCTORS = [
    ("Dr. Anita Rao", "Cardiology", "anita.rao@clinicdesk.test", 1200.0),
    ("Dr. Imran Shaikh", "Orthopaedics", "imran.shaikh@clinicdesk.test", 950.0),
    ("Dr. Kavya Nair", "Dermatology", "kavya.nair@clinicdesk.test", 800.0),
    ("Dr. Rohan Mehta", "Paediatrics", "rohan.mehta@clinicdesk.test", 650.0),
    ("Dr. Leela Krishnan", "General Medicine", "leela.k@clinicdesk.test", 500.0),
]

PATIENTS = [
    ("Meera Iyer", "+919845011223", "meera.iyer@example.test", (1992, 6, 14)),
    ("Rahul Verma", "+919845011224", "rahul.verma@example.test", (1985, 1, 30)),
    ("Sana Qureshi", "+919845011225", "sana.q@example.test", (1998, 11, 8)),
    ("Arjun Nair", "+919845011226", None, (1979, 4, 2)),
    ("Divya Menon", "+919845011227", "divya.menon@example.test", (2001, 9, 21)),
    ("Karthik Subbu", "+919845011228", None, (1990, 12, 12)),
    ("Nisha Pillai", "+919845011229", "nisha.p@example.test", (1988, 3, 5)),
    ("Vikram Joshi", "+919845011230", None, (1995, 7, 19)),
]

REASONS = [
    "Follow-up consultation",
    "Chest pain reported",
    "Knee injury follow-up",
    "Skin allergy review",
    "Annual health check",
    "Post-operative review",
    "Fever and body ache",
    "Routine blood work",
]


def reset(db) -> None:
    db.execute(delete(Appointment))
    db.execute(delete(Patient))
    db.execute(delete(Doctor))
    db.commit()


def seed(reset_first: bool = False) -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if reset_first:
            print("Clearing existing data...")
            reset(db)

        existing = db.scalar(select(func.count(Doctor.id))) or 0
        if existing:
            print(
                f"Skipping: {existing} doctor(s) already present. Use --reset to reseed."
            )
            return

        doctors = [
            Doctor(
                full_name=name,
                specialty=specialty,
                email=email,
                consultation_fee=fee,
            )
            for name, specialty, email, fee in DOCTORS
        ]
        db.add_all(doctors)
        db.flush()

        patients = [
            Patient(
                full_name=name,
                phone=phone,
                email=email,
                date_of_birth=datetime(year, month, day).date(),
            )
            for name, phone, email, (year, month, day) in PATIENTS
        ]
        db.add_all(patients)
        db.flush()

        rng = random.Random(42)
        now = datetime.now(timezone.utc)
        appointments: list[Appointment] = []

        # Past 14 days: finished consultations with realistic outcomes.
        past_slots: set[tuple[int, datetime]] = set()
        for day_offset in range(-14, 0):
            day = now + timedelta(days=day_offset)
            for _ in range(rng.randint(3, 7)):
                doctor = rng.choice(doctors)
                hour = rng.randint(9, 17)
                scheduled_at = day.replace(
                    hour=hour, minute=rng.choice([0, 30]), second=0, microsecond=0
                )
                if scheduled_at >= now:
                    continue
                key = (doctor.id, scheduled_at)
                if key in past_slots:
                    continue
                past_slots.add(key)
                status = rng.choices(
                    [
                        AppointmentStatus.COMPLETED,
                        AppointmentStatus.NO_SHOW,
                        AppointmentStatus.CANCELLED,
                    ],
                    weights=[80, 12, 8],
                )[0]
                appointments.append(
                    Appointment(
                        doctor_id=doctor.id,
                        patient_id=rng.choice(patients).id,
                        scheduled_at=scheduled_at,
                        duration_minutes=rng.choice([15, 30, 30, 45, 60]),
                        reason=rng.choice(REASONS),
                        status=status,
                    )
                )

        # Today and the next 10 days: the bookable schedule.
        for day_offset in range(0, 11):
            day = now + timedelta(days=day_offset)
            used_slots: set[tuple[int, datetime]] = set()
            for _ in range(rng.randint(2, 6)):
                doctor = rng.choice(doctors)
                hour = rng.randint(9, 17)
                scheduled_at = day.replace(
                    hour=hour, minute=rng.choice([0, 30]), second=0, microsecond=0
                )
                key = (doctor.id, scheduled_at)
                if key in used_slots:
                    continue
                used_slots.add(key)
                appointments.append(
                    Appointment(
                        doctor_id=doctor.id,
                        patient_id=rng.choice(patients).id,
                        scheduled_at=scheduled_at,
                        duration_minutes=rng.choice([15, 30, 45]),
                        reason=rng.choice(REASONS),
                        status=rng.choices(
                            [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED],
                            weights=[55, 45],
                        )[0],
                    )
                )

        db.add_all(appointments)
        db.commit()

        print(
            f"Seeded {len(doctors)} doctors, {len(patients)} patients, "
            f"{len(appointments)} appointments."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed ClinicDesk demo data")
    parser.add_argument(
        "--reset", action="store_true", help="Delete existing rows before seeding"
    )
    seed(parser.parse_args().reset)
