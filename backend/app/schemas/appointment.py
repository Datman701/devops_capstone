from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.appointment import AppointmentStatus
from app.schemas.common import DoctorRef, PatientRef

ALLOWED_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    # Terminal states cannot be moved again.
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


class AppointmentBase(BaseModel):
    doctor_id: int = Field(gt=0, examples=[1])
    patient_id: int = Field(gt=0, examples=[1])
    scheduled_at: datetime = Field(examples=["2026-10-20T10:30:00+05:30"])
    duration_minutes: int = Field(default=30, gt=0, le=240, examples=[30])
    reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=500)


class AppointmentCreate(AppointmentBase):
    status: AppointmentStatus = AppointmentStatus.SCHEDULED

    @field_validator("scheduled_at")
    @classmethod
    def _not_in_the_past(cls, value: datetime) -> datetime:
        # The UI posts near-future slots, so only clearly stale input is rejected.
        if value.tzinfo is None:
            raise ValueError("scheduled_at must be timezone aware")
        if value < datetime.now(timezone.utc) - timedelta(minutes=1):
            raise ValueError("scheduled_at cannot be in the past")
        return value


class AppointmentUpdate(BaseModel):
    doctor_id: int | None = Field(default=None, gt=0)
    patient_id: int | None = Field(default=None, gt=0)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=240)
    reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=500)
    status: AppointmentStatus | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "AppointmentUpdate":
        if not self.model_dump(exclude_unset=True):
            raise ValueError("at least one field must be supplied")
        return self


class StatusChange(BaseModel):
    status: AppointmentStatus
    notes: str | None = Field(default=None, max_length=500)


class AppointmentRead(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: AppointmentStatus
    doctor: DoctorRef
    patient: PatientRef
    created_at: datetime
    updated_at: datetime
