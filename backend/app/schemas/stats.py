from datetime import date, datetime

from pydantic import BaseModel, Field


class StatusCount(BaseModel):
    status: str
    count: int


class BusyDoctor(BaseModel):
    doctor_id: int
    full_name: str
    specialty: str
    count: int


class AppointmentStats(BaseModel):
    """Everything the dashboard KPI cards and activity feed need."""

    generated_at: datetime
    total: int = Field(description="Appointments matching the active filters")
    today: int = Field(description="Appointments scheduled for today")
    upcoming_7_days: int = Field(
        description="Appointments scheduled in the next 7 days"
    )
    by_status: dict[str, int]
    cancelled_rate: float = Field(
        description="0.0 - 1.0 share of cancelled appointments"
    )
    busiest_hour: int | None = Field(
        description="Hour of day with the most appointments"
    )
    busy_doctors: list[BusyDoctor]
    active_patients: int
    active_doctors: int
    latest: list["RecentAppointment"]


class RecentAppointment(BaseModel):
    id: int
    patient_name: str
    doctor_name: str
    scheduled_at: datetime
    status: str
    created_at: datetime


class DoctorScheduleDay(BaseModel):
    date: date
    total: int
    free_slots: int
