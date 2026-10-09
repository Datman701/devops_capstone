from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import DbSession, get_doctor_or_404, get_patient_or_404
from app.models import Appointment, AppointmentStatus
from app.schemas import (
    ALLOWED_TRANSITIONS,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    StatusChange,
)

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

_SLOT_CONFLICT = (
    "This doctor already has an appointment in that slot. "
    "Cancel the existing one or pick a different time."
)


def _load(db: Session, appointment_id: int) -> Appointment:
    stmt = (
        select(Appointment)
        .options(selectinload(Appointment.doctor), selectinload(Appointment.patient))
        .where(Appointment.id == appointment_id)
    )
    appointment = db.scalars(stmt).first()
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} not found",
        )
    return appointment


def _assert_slot_free(
    db: Session,
    doctor_id: int,
    scheduled_at: datetime,
    exclude_id: int | None = None,
) -> None:
    stmt = select(Appointment.id).where(
        Appointment.doctor_id == doctor_id,
        Appointment.scheduled_at == scheduled_at,
        Appointment.status != AppointmentStatus.CANCELLED,
    )
    if exclude_id is not None:
        stmt = stmt.where(Appointment.id != exclude_id)
    if db.scalars(stmt).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_SLOT_CONFLICT)


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    db: DbSession,
    doctor_id: int | None = Query(default=None, description="Filter by doctor"),
    patient_id: int | None = Query(default=None, description="Filter by patient"),
    status_filter: AppointmentStatus | None = Query(
        default=None, alias="status", description="Filter by appointment status"
    ),
    date_from: datetime | None = Query(
        default=None, description="ISO-8601 lower bound"
    ),
    date_to: datetime | None = Query(default=None, description="ISO-8601 upper bound"),
    upcoming_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Appointment]:
    stmt = select(Appointment).options(
        selectinload(Appointment.doctor), selectinload(Appointment.patient)
    )
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter)
    if date_from is not None:
        stmt = stmt.where(Appointment.scheduled_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Appointment.scheduled_at <= date_to)
    if upcoming_only:
        stmt = stmt.where(
            Appointment.scheduled_at >= datetime.now(timezone.utc),
            Appointment.status.in_(
                [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
            ),
        )
    stmt = stmt.order_by(Appointment.scheduled_at).offset(skip).limit(limit)
    return list(db.scalars(stmt))


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, db: DbSession) -> Appointment:
    doctor = get_doctor_or_404(db, payload.doctor_id)
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Doctor {doctor.full_name} is not accepting appointments",
        )
    get_patient_or_404(db, payload.patient_id)

    _assert_slot_free(db, payload.doctor_id, payload.scheduled_at)

    appointment = Appointment(**payload.model_dump())
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        # The partial unique index is the real guard against a concurrent insert.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_SLOT_CONFLICT
        ) from None
    return _load(db, appointment.id)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def read_appointment(appointment_id: int, db: DbSession) -> Appointment:
    return _load(db, appointment_id)


@router.put("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int, payload: AppointmentUpdate, db: DbSession
) -> Appointment:
    appointment = _load(db, appointment_id)
    changes = payload.model_dump(exclude_unset=True)

    new_status = changes.get("status")
    if new_status is not None and new_status != appointment.status:
        allowed = ALLOWED_TRANSITIONS[appointment.status]
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot move an appointment from '{appointment.status.value}' "
                    f"to '{new_status.value}'. Allowed: "
                    f"{sorted(s.value for s in allowed) or 'none (terminal state)'}"
                ),
            )

    new_doctor_id = changes.get("doctor_id", appointment.doctor_id)
    new_scheduled_at = changes.get("scheduled_at", appointment.scheduled_at)
    if (
        new_doctor_id != appointment.doctor_id
        or new_scheduled_at != appointment.scheduled_at
    ):
        if new_doctor_id != appointment.doctor_id:
            get_doctor_or_404(db, new_doctor_id)
        # A cancelled appointment keeps its slot free for everyone.
        effective_status = new_status or appointment.status
        if effective_status != AppointmentStatus.CANCELLED:
            _assert_slot_free(
                db, new_doctor_id, new_scheduled_at, exclude_id=appointment.id
            )

    if "patient_id" in changes:
        get_patient_or_404(db, changes["patient_id"])

    for field, value in changes.items():
        setattr(appointment, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_SLOT_CONFLICT
        ) from None
    return _load(db, appointment.id)


@router.patch("/{appointment_id}/status", response_model=AppointmentRead)
def change_status(
    appointment_id: int, payload: StatusChange, db: DbSession
) -> Appointment:
    appointment = _load(db, appointment_id)
    if payload.status == appointment.status:
        return appointment

    allowed = ALLOWED_TRANSITIONS[appointment.status]
    if payload.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot move an appointment from '{appointment.status.value}' "
                f"to '{payload.status.value}'. Allowed: "
                f"{sorted(s.value for s in allowed) or 'none (terminal state)'}"
            ),
        )
    appointment.status = payload.status
    if payload.notes is not None:
        appointment.notes = payload.notes
    db.commit()
    return _load(db, appointment.id)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(appointment_id: int, db: DbSession) -> Response:
    """Cancels rather than hard-deletes, so the audit trail and the activity
    feed keep working. Cancelling also frees the doctor's slot for rebooking.

    Respects the same state machine as PATCH /status: a completed or no-show
    appointment is final and cannot be cancelled afterwards.
    """
    appointment = _load(db, appointment_id)
    if appointment.status == AppointmentStatus.CANCELLED:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if AppointmentStatus.CANCELLED not in ALLOWED_TRANSITIONS[appointment.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot cancel an appointment with status "
                f"'{appointment.status.value}' because it is a terminal state."
            ),
        )

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{appointment_id}/history")
def appointment_history(appointment_id: int, db: DbSession) -> dict:
    appointment = _load(db, appointment_id)
    return {
        "id": appointment.id,
        "status": appointment.status.value,
        "allowed_next": sorted(
            s.value for s in ALLOWED_TRANSITIONS[appointment.status]
        ),
        "created_at": appointment.created_at,
        "updated_at": appointment.updated_at,
    }


@router.get("/{doctor_id}/availability")
def doctor_availability(
    doctor_id: int,
    db: DbSession,
    day: datetime | None = Query(
        default=None, description="Any datetime within the day"
    ),
) -> dict:
    """Free slots for a doctor on a given day, 30-minute granularity."""
    get_doctor_or_404(db, doctor_id)
    target = day or datetime.now(timezone.utc)
    start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    busy = db.scalars(
        select(Appointment.scheduled_at).where(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_at >= start,
            Appointment.scheduled_at < end,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
    ).all()
    booked = {
        slot.replace(tzinfo=start.tzinfo) if slot.tzinfo else slot for slot in busy
    }

    slots = []
    cursor = start
    while cursor < end:
        if cursor.hour >= 9 and cursor.hour < 18 and cursor not in booked:
            slots.append(cursor.isoformat())
        cursor += timedelta(minutes=30)

    return {
        "doctor_id": doctor_id,
        "date": start.date().isoformat(),
        "booked": len(booked),
        "free_slots": slots,
    }


__all__ = ["router"]
