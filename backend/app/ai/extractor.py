"""
extractor.py - Structured Meeting Extraction via Multi-Provider Intelligence
"""

import json
import logging
import re
from typing import Dict, Any, Optional

from app.config.settings import settings
from app.ai.reasoning_engine import reasoning_engine, clean_and_parse_json
from app.ai.normalizer import clean_doctor_name, is_valid_person_name
from app.ai.meeting_extractor import parse_date_expression

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an AI intelligence extractor for Ask PulseCRM.
Extract structured clinical relationship details from field interaction notes.

Return ONLY valid JSON matching this schema:
{
  "doctor_name": string or null,       // e.g. "Dr. Rajesh Sharma"
  "hospital": string or null,          // e.g. "Apollo Hospital"
  "specialization": string or null,    // e.g. "Cardiology"
  "city": string or null,              // e.g. "Mumbai", "Visakhapatnam"
  "phone": string or null,             // Explicit phone number if stated
  "email": string or null,             // Explicit email address if stated
  "products_discussed": string or null,// e.g. "CardioPress-50, LipiGuard"
  "follow_up_date": string or null,    // ISO 8601 datetime format (e.g. "2026-09-15T10:00:00")
  "meeting_summary": string or null    // Concise summary of discussion points
}

CRITICAL RULES:
- Never fabricate doctor details, phone numbers, or emails.
- If exact information is not in the text, return null.
- Preserve explicit phone numbers, email addresses, and follow-up dates exactly when present.
"""


def extract_meeting_details(text: str) -> str:
    """
    Extract structured meeting information using Gemini or Groq model pool with bounded retries.
    Returns a valid JSON string.
    """
    if not text or not text.strip():
        return json.dumps({
            "doctor_name": None,
            "hospital": None,
            "specialization": None,
            "city": None,
            "phone": None,
            "email": None,
            "products_discussed": None,
            "follow_up_date": None,
            "meeting_summary": None,
        })

    user_prompt = f"Meeting Notes:\n\"{text}\""

    # 1. Try Gemini
    if reasoning_engine.gemini_client:
        try:
            from google.genai import types
            model_id = settings.GEMINI_MODEL or "gemini-3.7-flash"
            resp = reasoning_engine.gemini_client.models.generate_content(
                model=model_id,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            parsed = clean_and_parse_json(resp.text)
            if parsed:
                return json.dumps(parsed)
        except Exception as e:
            logger.warning(f"[Extractor] Gemini extraction failed: {e}")

    # 2. Try Groq Pool
    if reasoning_engine.groq_client:
        candidate_models = [
            "openai/gpt-oss-120b",
            "qwen/qwen3.8-27b",
            "qwen/qwen3.6-27b",
            "groq/compound",
        ]
        for model_id in candidate_models:
            try:
                comp = reasoning_engine.groq_client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw_content = comp.choices[0].message.content
                parsed = clean_and_parse_json(raw_content)
                if parsed:
                    return json.dumps(parsed)
            except Exception as e:
                logger.warning(f"[Extractor] Groq {model_id} extraction failed: {e}")
                continue

    # 3. Deterministic Fallback Extraction
    return _deterministic_meeting_extraction(text)


def _deterministic_meeting_extraction(text: str) -> str:
    """Fallback extraction when all LLMs are unreachable."""
    doc_match = re.search(r"(?:dr\.?\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
    doc_name = None
    if "dr " in text.lower() or "dr. " in text.lower() or "doctor " in text.lower():
        m = re.search(r"(?:dr\.?|doctor)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
        if m:
            doc_name = clean_doctor_name(m.group(1))

    hosp_match = re.search(r"([A-Za-z\s]+(?:Hospital|Clinic|Care|KIMS|Apollo|Manipal))", text, re.IGNORECASE)
    hospital = hosp_match.group(1).strip() if hosp_match else None

    # Products
    from app.ai.fuzzy_matcher import match_product_from_transcript
    prod = match_product_from_transcript(text)

    # Follow-up date
    dt_p = parse_date_expression(text)
    follow_up_date = dt_p[0].isoformat() if dt_p else None

    data = {
        "doctor_name": doc_name,
        "hospital": hospital,
        "specialization": "Cardiology" if "cardio" in text.lower() else "General Medicine",
        "city": "Mumbai" if "mumbai" in text.lower() else "Hyderabad" if "hyderabad" in text.lower() else None,
        "phone": None,
        "email": None,
        "products_discussed": prod,
        "follow_up_date": follow_up_date,
        "meeting_summary": text.strip(),
    }

    return json.dumps(data)