from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, get_doctor_or_404, get_patient_or_404
from app.models import Doctor, Patient
from app.schemas import (
    DoctorCreate,
    DoctorRead,
    PatientCreate,
    PatientRead,
)

router = APIRouter(prefix="/api", tags=["directory"])


@router.get("/doctors", response_model=list[DoctorRead])
def list_doctors(
    db: DbSession,
    include_inactive: bool = Query(default=False),
) -> list[Doctor]:
    stmt = select(Doctor).order_by(Doctor.full_name)
    if not include_inactive:
        stmt = stmt.where(Doctor.is_active.is_(True))
    return list(db.scalars(stmt))


@router.post("/doctors", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(payload: DoctorCreate, db: DbSession) -> Doctor:
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A doctor with email {payload.email} already exists",
        ) from None
    db.refresh(doctor)
    return doctor


@router.get("/doctors/{doctor_id}", response_model=DoctorRead)
def read_doctor(doctor_id: int, db: DbSession) -> Doctor:
    return get_doctor_or_404(db, doctor_id)


@router.get("/patients", response_model=list[PatientRead])
def list_patients(
    db: DbSession, skip: int = 0, limit: int = Query(100, le=500)
) -> list[Patient]:
    stmt = select(Patient).order_by(Patient.full_name).offset(skip).limit(limit)
    return list(db.scalars(stmt))


@router.post(
    "/patients", response_model=PatientRead, status_code=status.HTTP_201_CREATED
)
def create_patient(payload: PatientCreate, db: DbSession) -> Patient:
    patient = Patient(**payload.model_dump())
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A patient with phone {payload.phone} already exists",
        ) from None
    db.refresh(patient)
    return patient


@router.get("/patients/{patient_id}", response_model=PatientRead)
def read_patient(patient_id: int, db: DbSession) -> Patient:
    return get_patient_or_404(db, patient_id)


__all__ = ["router"]
