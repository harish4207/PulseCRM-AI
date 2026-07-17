from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)

    doctor_name = Column(String(100), nullable=False)

    specialization = Column(String(100), nullable=False)

    hospital = Column(String(150), nullable=False)

    city = Column(String(100), nullable=False)

    phone = Column(String(20), unique=True)

    email = Column(String(150), unique=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())