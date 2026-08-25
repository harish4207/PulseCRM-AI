import json
from typing import Optional

from app.config.settings import settings
from app.ai.extractor import extract_meeting_details
from app.schemas.ai_schema import AIExtraction


class ExtractionError(Exception):
    pass


def extract_and_validate(meeting_text: str) -> AIExtraction:
    """
    Call the existing extractor to get raw AI output, clean it, parse JSON, and validate via Pydantic.

    Raises:
      ExtractionError on parse/validation issues
      RuntimeError if GROQ_API_KEY is not available
    """
    if not meeting_text or not meeting_text.strip():
        raise ExtractionError("Empty meeting text provided")

    if not settings.GROQ_API_KEY:
        raise RuntimeError("AI processing is unavailable because the Groq API key is not configured.")

    try:
        raw = extract_meeting_details(meeting_text)
    except Exception as exc:
        raise RuntimeError("AI processing could not reach Groq. Please try again in a moment.") from exc

    if not raw:
        raise ExtractionError("The AI model returned no structured output.")

    cleaned = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(cleaned)
    except Exception as exc:
        raise ExtractionError("The AI model returned malformed structured output. Please rephrase the notes and try again.") from exc

    try:
        extraction = AIExtraction(**data)
    except Exception as exc:
        raise ExtractionError("The extracted meeting data failed validation. Please try a clearer note.") from exc

    return extraction


def try_extract_with_optional_live(meeting_text: str, mock_extraction: Optional[dict] = None) -> AIExtraction:
    """
    Helper that will use mock_extraction if provided (for tests / blocked LLM), or call the live extractor when GROQ_API_KEY present.
    """
    if mock_extraction is not None:
        try:
            return AIExtraction(**mock_extraction)
        except Exception as exc:
            raise ExtractionError("The sample extraction payload failed validation.") from exc

    return extract_and_validate(meeting_text)
