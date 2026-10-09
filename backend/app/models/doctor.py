from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialty: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    consultation_fee: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    appointments: Mapped[list["Appointment"]] = relationship(  # noqa: F821
        back_populates="doctor",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Doctor {self.id} {self.full_name}>"
