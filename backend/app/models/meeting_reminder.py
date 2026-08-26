from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.database import Base
from app.models.user import User
from app.models.scheduled_meeting import ScheduledMeeting


class MeetingReminder(Base):
    __tablename__ = "meeting_reminders"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("scheduled_meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remind_at = Column(DateTime, nullable=False)
    remind_offset_minutes = Column(Integer, default=30)
    status = Column(String(50), default="pending")  # pending, triggered, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meeting = relationship("ScheduledMeeting", back_populates="reminders")
