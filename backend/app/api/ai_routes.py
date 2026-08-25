import base64
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from groq import Groq

from app.database.dependencies import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.config.settings import settings


class LogMeetingRequest(BaseModel):
    meeting_text: str


router = APIRouter(prefix="/ai")


@router.post("/log-meeting")
def log_meeting(req: LogMeetingRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not req.meeting_text or not req.meeting_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="meeting_text is required")

    from app.ai.graph import run_state_graph

    try:
        result = run_state_graph(db, req.meeting_text, current_user.id)
    except RuntimeError as e:
        # Live LLM blocked (GROQ_API_KEY missing)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI workflow error: {str(e)}")

    if not isinstance(result, dict):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected graph result")

    if not result.get("success"):
        return result

    return result


@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe recorded audio using Groq Whisper.
    Accepts raw audio binary stream (audio/webm, audio/wav, audio/mp4, etc.)
    or JSON payload with base64 encoded audio.
    """
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GROQ_API_KEY is not configured")

    content_type = request.headers.get("content-type", "").lower()
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            audio_b64 = body.get("audio_data") or body.get("audio_base64")
            if not audio_b64:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No usable audio was recorded. Please try recording again.")
            audio_bytes = base64.b64decode(audio_b64)
            filename = body.get("filename", "recording.webm")
            target_mime = "audio/webm"
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid audio payload: {e}")
    else:
        audio_bytes = await request.body()
        filename = "recording.webm"
        target_mime = "audio/webm"

        if "wav" in content_type:
            filename = "recording.wav"
            target_mime = "audio/wav"
        elif "mp4" in content_type or "m4a" in content_type or "aac" in content_type:
            filename = "recording.m4a"
            target_mime = "audio/mp4"
        elif "mpeg" in content_type or "mp3" in content_type:
            filename = "recording.mp3"
            target_mime = "audio/mpeg"
        elif "ogg" in content_type:
            filename = "recording.ogg"
            target_mime = "audio/ogg"
        elif "webm" in content_type:
            filename = "recording.webm"
            target_mime = "audio/webm"

    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No usable audio was recorded. Please try recording again."
        )

    try:
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        transcription = groq_client.audio.transcriptions.create(
            file=(filename, audio_bytes, target_mime),
            model="whisper-large-v3",
            response_format="json"
        )
        transcript_text = transcription.text if hasattr(transcription, "text") else str(transcription)
        return {
            "success": True,
            "transcript": transcript_text.strip()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription error: {str(e)}"
        )