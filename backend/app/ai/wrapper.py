import json
import logging
from typing import Optional

from app.config.settings import settings
from app.ai.extractor import extract_meeting_details
from app.schemas.ai_schema import AIExtraction
from app.ai.reasoning_engine import clean_and_parse_json

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    pass


def extract_and_validate(meeting_text: str) -> AIExtraction:
    """
    Call the extractor to get structured AI output, parse JSON, and validate via Pydantic.
    """
    if not meeting_text or not meeting_text.strip():
        raise ExtractionError("Empty meeting text provided")

    try:
        raw = extract_meeting_details(meeting_text)
    except Exception as exc:
        logger.warning(f"[Wrapper] Extractor call failed: {exc}")
        raw = None

    if not raw:
        raise ExtractionError("The AI model returned no structured output.")

    data = clean_and_parse_json(raw)
    if not data:
        try:
            data = json.loads(raw.replace("```json", "").replace("```", "").strip())
        except Exception as exc:
            raise ExtractionError("The AI model returned malformed structured output. Please rephrase the notes and try again.") from exc

    # Ensure required doctor_name or fallback exists
    if not data.get("meeting_summary"):
        data["meeting_summary"] = meeting_text.strip()

    try:
        extraction = AIExtraction(**data)
    except Exception as exc:
        logger.warning(f"[Wrapper] Pydantic validation warning: {exc}. Attempting safe normalization.")
        # Normalize fields safely
        clean_data = {
            "doctor_name": data.get("doctor_name"),
            "hospital": data.get("hospital"),
            "specialization": data.get("specialization"),
            "city": data.get("city"),
            "phone": data.get("phone"),
            "email": data.get("email"),
            "products_discussed": data.get("products_discussed"),
            "follow_up_date": data.get("follow_up_date"),
            "meeting_summary": data.get("meeting_summary") or meeting_text.strip(),
        }
        extraction = AIExtraction(**clean_data)

    return extraction


def try_extract_with_optional_live(meeting_text: str, mock_extraction: Optional[dict] = None) -> AIExtraction:
    """
    Helper that will use mock_extraction if provided (for tests / blocked LLM), or call the live extractor.
    """
    if mock_extraction is not None:
        try:
            return AIExtraction(**mock_extraction)
        except Exception as exc:
            raise ExtractionError("The sample extraction payload failed validation.") from exc

    return extract_and_validate(meeting_text)
