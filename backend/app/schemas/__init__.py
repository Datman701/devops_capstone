from app.schemas.appointment import (
    ALLOWED_TRANSITIONS,
    AppointmentBase,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    StatusChange,
)
from app.schemas.common import (
    DoctorBase,
    DoctorCreate,
    DoctorRead,
    DoctorRef,
    PatientBase,
    PatientCreate,
    PatientRead,
    PatientRef,
)
from app.schemas.stats import (
    AppointmentStats,
    BusyDoctor,
    DoctorScheduleDay,
    RecentAppointment,
    StatusCount,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentRead",
    "AppointmentStats",
    "AppointmentUpdate",
    "BusyDoctor",
    "DoctorBase",
    "DoctorCreate",
    "DoctorRead",
    "DoctorRef",
    "DoctorScheduleDay",
    "PatientBase",
    "PatientCreate",
    "PatientRead",
    "PatientRef",
    "RecentAppointment",
    "StatusChange",
    "StatusCount",
]
