from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.models.user import User
from app.models.hcp import HCP


class ScheduledMeeting(Base):
    __tablename__ = "scheduled_meetings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hcp_id = Column(Integer, ForeignKey("hcps.id"), nullable=False)
    meeting_time = Column(DateTime, nullable=False)
    meeting_time_display = Column(String(100), nullable=True)
    location = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="scheduled")  # scheduled, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hcp = relationship("HCP", foreign_keys=[hcp_id], lazy="joined")
    reminders = relationship("MeetingReminder", back_populates="meeting", cascade="all, delete-orphan")
