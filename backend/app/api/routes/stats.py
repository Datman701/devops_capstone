from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession
from app.models import Appointment, AppointmentStatus, Doctor, Patient
from app.schemas import AppointmentStats, BusyDoctor, RecentAppointment

router = APIRouter(prefix="/api", tags=["dashboard"])

OPEN_STATUSES = (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED)


@router.get("/appointments/stats", response_model=AppointmentStats)
def appointment_stats(
    db: DbSession,
    doctor_id: int | None = Query(default=None),
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> AppointmentStats:
    """Single aggregation powering every KPI card and the activity feed."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    filters = []
    if doctor_id is not None:
        filters.append(Appointment.doctor_id == doctor_id)
    if status_filter is not None:
        filters.append(Appointment.status == status_filter)
    if date_from is not None:
        filters.append(Appointment.scheduled_at >= date_from)
    if date_to is not None:
        filters.append(Appointment.scheduled_at <= date_to)

    total = db.scalar(select(func.count(Appointment.id)).where(*filters)) or 0

    today = (
        db.scalar(
            select(func.count(Appointment.id)).where(
                *filters,
                Appointment.scheduled_at >= day_start,
                Appointment.scheduled_at < day_start + timedelta(days=1),
            )
        )
        or 0
    )

    upcoming_7_days = (
        db.scalar(
            select(func.count(Appointment.id)).where(
                *filters,
                Appointment.scheduled_at >= now,
                Appointment.scheduled_at < day_start + timedelta(days=7),
                Appointment.status.in_(OPEN_STATUSES),
            )
        )
        or 0
    )

    by_status = {member.value: 0 for member in AppointmentStatus}
    for row_status, count in db.execute(
        select(Appointment.status, func.count(Appointment.id))
        .where(*filters)
        .group_by(Appointment.status)
    ).all():
        by_status[row_status.value] = count

    cancelled = by_status.get(AppointmentStatus.CANCELLED.value, 0)
    cancelled_rate = round(cancelled / total, 4) if total else 0.0

    hour_rows = db.execute(
        select(
            func.extract("hour", Appointment.scheduled_at).label("hour"),
            func.count(Appointment.id).label("count"),
        )
        .where(*filters)
        .group_by("hour")
    ).all()
    busiest_hour = (
        int(max(hour_rows, key=lambda row: row.count).hour) if hour_rows else None
    )

    busy_doctors = [
        BusyDoctor.model_validate(
            {
                "doctor_id": row.doctor_id,
                "full_name": row.full_name,
                "specialty": row.specialty,
                "count": row.count,
            }
        )
        for row in db.execute(
            select(
                Doctor.id.label("doctor_id"),
                Doctor.full_name,
                Doctor.specialty,
                func.count(Appointment.id).label("count"),
            )
            .join(Appointment, Appointment.doctor_id == Doctor.id)
            .where(*filters)
            .group_by(Doctor.id, Doctor.full_name, Doctor.specialty)
            .order_by(func.count(Appointment.id).desc(), Doctor.full_name)
            .limit(5)
        ).all()
    ]

    latest = [
        RecentAppointment(
            id=appointment.id,
            patient_name=appointment.patient.full_name,
            doctor_name=appointment.doctor.full_name,
            scheduled_at=appointment.scheduled_at,
            status=appointment.status.value,
            created_at=appointment.created_at,
        )
        for appointment in db.scalars(
            select(Appointment)
            .options(
                selectinload(Appointment.doctor), selectinload(Appointment.patient)
            )
            .where(*filters)
            .order_by(Appointment.created_at.desc())
            .limit(8)
        ).all()
    ]

    return AppointmentStats(
        generated_at=now,
        total=total,
        today=today,
        upcoming_7_days=upcoming_7_days,
        by_status=by_status,
        cancelled_rate=cancelled_rate,
        busiest_hour=busiest_hour,
        busy_doctors=busy_doctors,
        active_patients=db.scalar(select(func.count(Patient.id))) or 0,
        active_doctors=db.scalar(
            select(func.count(Doctor.id)).where(Doctor.is_active.is_(True))
        )
        or 0,
        latest=latest,
    )


__all__ = ["router"]
