from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import EmailAddress


class DoctorBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=120, examples=["Dr. Anita Rao"])
    specialty: str = Field(min_length=2, max_length=80, examples=["Cardiology"])
    email: EmailAddress = Field(examples=["anita.rao@clinicdesk.test"])
    consultation_fee: float = Field(default=0, ge=0, examples=[750.0])


class DoctorCreate(DoctorBase):
    pass


class DoctorRead(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class PatientBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=120, examples=["Meera Iyer"])
    phone: str = Field(min_length=6, max_length=20, examples=["+91 98450 11223"])
    email: EmailAddress | None = Field(default=None)
    date_of_birth: date | None = None


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class DoctorRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    specialty: str


class PatientRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str


__all__ = [
    "DoctorBase",
    "DoctorCreate",
    "DoctorRead",
    "DoctorRef",
    "PatientBase",
    "PatientCreate",
    "PatientRead",
    "PatientRef",
]
