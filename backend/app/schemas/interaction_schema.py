from pydantic import BaseModel
from datetime import datetime


class InteractionCreate(BaseModel):
    user_id: int
    hcp_id: int
    meeting_notes: str
    products_discussed: str
    follow_up_date: datetime


class InteractionResponse(InteractionCreate):
    id: int
    ai_summary: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True