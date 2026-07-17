from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    hcp_id = Column(Integer, ForeignKey("hcps.id"))

    meeting_notes = Column(Text, nullable=False)

    ai_summary = Column(Text)

    products_discussed = Column(Text)

    follow_up_date = Column(DateTime)

    created_at = Column(DateTime(timezone=True), server_default=func.now())