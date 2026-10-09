"""Shared pytest fixtures.

Tests run against a dedicated `clinic_test` database, never the development
`clinic` database. Each test gets a session bound to a connection wrapped in
an outer transaction that is always rolled back, so tests cannot leak rows
into each other and the schema is created once per run.
"""

import os
from collections.abc import Generator
from datetime import datetime, time, timedelta, timezone

import pytest

# Point the application at the test database *before* app modules import
# settings, because settings.database_url is resolved at import time.
_DEV_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://clinic:clinic@localhost:5432/clinic"
)
_TEST_URL = (
    os.environ.get("TEST_DATABASE_URL") or _DEV_URL.rsplit("/", 1)[0] + "/clinic_test"
)
os.environ["DATABASE_URL"] = _TEST_URL
os.environ["APP_ENV"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Appointment, AppointmentStatus, Doctor, Patient  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create the schema once for the whole run by applying Alembic migrations.

    Running migrations (rather than metadata.create_all) means the tests also
    exercise the migration scripts themselves.
    """
    engine = create_engine(_TEST_URL, pool_pre_ping=True)

    alembic_cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", _TEST_URL)

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    command.upgrade(alembic_cfg, "head")

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(test_engine: Engine) -> Generator[Session, None, None]:
    """Function-scoped session rolled back at the end of every test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    # create_savepoint mode turns handler-level db.commit() calls into savepoint
    # releases, so the outer rollback still discards every row.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def doctor(db: Session) -> Doctor:
    row = Doctor(
        full_name="Dr. Test Physician",
        specialty="Cardiology",
        email="test.physician@clinicdesk.test",
        consultation_fee=1000.0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def other_doctor(db: Session) -> Doctor:
    row = Doctor(
        full_name="Dr. Second Opinion",
        specialty="Dermatology",
        email="second.opinion@clinicdesk.test",
        consultation_fee=800.0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def patient(db: Session) -> Patient:
    row = Patient(
        full_name="Test Patient",
        phone="+919000000001",
        email="test.patient@clinicdesk.test",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def other_patient(db: Session) -> Patient:
    row = Patient(full_name="Second Patient", phone="+919000000002")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def future_slot() -> datetime:
    """A future time snapped to a 30-minute boundary inside clinic hours.

    Snapping matters: /availability only offers :00 and :30 slots between
    09:00 and 18:00, so an off-grid timestamp could never appear as free.
    """
    day = (datetime.now(timezone.utc) + timedelta(days=30)).date()
    return datetime.combine(day, time(hour=10, minute=0), tzinfo=timezone.utc)


def appointment_payload(
    doctor: Doctor,
    patient: Patient,
    scheduled_at: datetime,
    **overrides,
) -> dict:
    payload = {
        "doctor_id": doctor.id,
        "patient_id": patient.id,
        "scheduled_at": scheduled_at.isoformat(),
        "duration_minutes": 30,
        "reason": "Routine consultation",
        "status": AppointmentStatus.SCHEDULED.value,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def make_appointment(db: Session):
    """Factory for building appointments directly in the database."""

    def _factory(
        doctor: Doctor,
        patient: Patient,
        scheduled_at: datetime,
        status: AppointmentStatus = AppointmentStatus.SCHEDULED,
        **overrides,
    ) -> Appointment:
        row = Appointment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            scheduled_at=scheduled_at,
            duration_minutes=overrides.pop("duration_minutes", 30),
            reason=overrides.pop("reason", "Seeded by test"),
            status=status,
            **overrides,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    return _factory
