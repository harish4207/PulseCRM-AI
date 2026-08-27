import base64
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from groq import Groq

from app.database.dependencies import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.config.settings import settings

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.warning(f"[ai_routes] Error in log_meeting graph: {e}")
        return {
            "success": False,
            "message": "We could not process this meeting note automatically. Please verify the doctor and hospital details and try again.",
            "error": "PROCESSING_ERROR"
        }

    if not isinstance(result, dict):
        return {
            "success": False,
            "message": "Unexpected error processing meeting.",
            "error": "UNEXPECTED_RESULT"
        }

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


# ---------------------------------------------------------------------------
# Unified Ask PulseCRM Copilot Endpoint (Text + Voice)
# ---------------------------------------------------------------------------

class CopilotChatRequest(BaseModel):
    message: Optional[str] = None
    transcript: Optional[str] = None  # Compatibility alias
    conversation_id: Optional[str] = None
    input_mode: str = "text"  # "text" or "voice"
    history: List[Dict[str, str]] = []
    selected_hcp_id: Optional[int] = None
    selected_hcp_name: Optional[str] = None
    pending_confirmation: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    preferred_provider: Optional[str] = None


def _process_copilot_query(
    req: CopilotChatRequest,
    db: Session,
    current_user: User,
) -> Dict[str, Any]:
    text = (req.message or req.transcript or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message/transcript is required and cannot be empty",
        )

    from app.ai.voice_copilot_graph import run_voice_copilot_graph

    try:
        result = run_voice_copilot_graph(
            db=db,
            transcript=text,
            user_id=current_user.id,
            history=req.history or [],
            current_hcp_id=req.selected_hcp_id,
            current_hcp_name=req.selected_hcp_name,
            pending_confirmation=req.pending_confirmation,
            pending_action=req.pending_action,
            preferred_provider=req.preferred_provider,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Copilot error: {str(e)}",
        )

    logger.info(
        f"[COPILOT TRACE] User={current_user.id} | ConvID={req.conversation_id} | "
        f"Input='{text[:60]}' | Mode={req.input_mode} | ActiveHCP={req.selected_hcp_name} | "
        f"Intent={result.get('intent')} | PendingConf={result.get('pending_confirmation')} | "
        f"Response='{result.get('response', '')[:80]}...'"
    )

    if not result.get("success"):
        return {
            "success": False,
            "response": result.get("response", "Something went wrong. Please try again."),
            "language": result.get("language", "en"),
            "intent": result.get("intent", "UNKNOWN"),
            "hcp_id": None,
            "hcp_name": None,
            "pending_confirmation": False,
            "pending_action": None,
            "card_data": None,
            "conversation_id": req.conversation_id,
            "input_mode": req.input_mode,
        }

    return {
        "success": True,
        "response": result.get("response", ""),
        "language": result.get("language", "en"),
        "intent": result.get("intent", "UNKNOWN"),
        "hcp_id": result.get("hcp_id"),
        "hcp_name": result.get("hcp_name"),
        "pending_confirmation": result.get("pending_confirmation", False),
        "pending_action": result.get("pending_action"),
        "card_data": result.get("card_data"),
        "confidence": result.get("confidence", 1.0),
        "conversation_id": req.conversation_id,
        "input_mode": req.input_mode,
    }


@router.post("/copilot/chat")
def copilot_chat(
    req: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified Multimodal Copilot endpoint for text typing and voice speech.
    Uses identical LangGraph pipeline, CRM tools, context memory, and confirmation system.
    """
    return _process_copilot_query(req, db, current_user)


@router.post("/voice/chat")
def voice_chat_alias(
    req: CopilotChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Backwards-compatible Voice Copilot endpoint alias.
    """
    return _process_copilot_query(req, db, current_user)