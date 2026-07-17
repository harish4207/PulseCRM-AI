from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.ai.meeting_processor import process_meeting

router = APIRouter()


@router.post("/ai/log-meeting")
def log_meeting(
    meeting_text: str,
    user_id: int,
    db: Session = Depends(get_db)
):
    return process_meeting(
        db=db,
        meeting_text=meeting_text,
        user_id=user_id
    )