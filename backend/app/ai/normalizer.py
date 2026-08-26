"""
normalizer.py - Transcript Normalization for Ask PulseCRM Voice Copilot.

Normalizes:
- Unicode, whitespace, and capitalization
- Common Whisper speech-to-text artifacts
- Telugu postpositions ("tho", "ni", "ki", "lo", "gurinchi", "garu", "gaaru")
- Known CRM vocabulary (medicines, doctors, hospitals, follow-up phrases)
"""

import re
import unicodedata
from typing import Dict, Any, Tuple, Optional, List

# Product vocabulary map for fuzzy STT corrections
PRODUCT_STT_MAP = {
    "cardio press 50": "CardioPress-50",
    "cardiopress 50": "CardioPress-50",
    "cardio press50": "CardioPress-50",
    "cardiopress50": "CardioPress-50",
    "cardiopress": "CardioPress-50",
    "cardio press 75": "CardioPress-75",
    "cardiopress 75": "CardioPress-75",
    "cardio press 100": "CardioPress-100",
    "cardiopress 100": "CardioPress-100",
    "amlo pulse": "AmloPulse",
    "amlopulse": "AmloPulse",
    "glyco care": "GlycoCare",
    "glycocare": "GlycoCare",
    "neuro calm": "NeuroCalm",
    "neurocalm": "NeuroCalm",
    "lipid guard": "LipidGuard",
    "lipidguard": "LipidGuard",
    "respi clear": "RespiClear",
    "respiclear": "RespiClear",
    "cancer medicine": "Cancer Medicine",
}

# STT phrase corrections
PHRASE_STT_MAP = {
    "follow app": "follow-up",
    "followup": "follow-up",
    "follow up": "follow-up",
    "docter": "doctor",
    "dr.": "Dr.",
    "dr ": "Dr. ",
}

TELUGU_POSTPOSITIONS = [
    r"\b(?:gaaru|garu|గారు)\b",
    r"\b(?:tho|తో)\b",
    r"\b(?:ni|ని)\b",
    r"\b(?:ki|కి|ku|కు)\b",
    r"\b(?:lo|లో)\b",
    r"\b(?:gurinchi|గురించి)\b",
    r"\b(?:eppudu|ఎప్పుడు)\b",
    r"\b(?:cheppu|చెప్పు)\b",
]

def normalize_transcript(raw_transcript: str) -> str:
    """
    Apply multi-stage normalization on spoken transcript.
    """
    if not raw_transcript:
        return ""

    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", raw_transcript).strip()

    # 2. Collapse whitespace
    text = " ".join(text.split())

    # 3. Known product normalization
    lower_text = text.lower()
    for stt_variant, standard_prod in PRODUCT_STT_MAP.items():
        pattern = rf"\b{re.escape(stt_variant)}\b"
        text = re.sub(pattern, standard_prod, text, flags=re.IGNORECASE)

    # 4. Known phrase corrections
    for wrong_phrase, correct_phrase in PHRASE_STT_MAP.items():
        pattern = rf"\b{re.escape(wrong_phrase)}\b"
        text = re.sub(pattern, correct_phrase, text, flags=re.IGNORECASE)

    return text.strip()


def extract_clean_search_tokens(text: str) -> str:
    """
    Strip common Telugu postpositions and filler words for clean entity search.
    """
    clean = text
    for pp in TELUGU_POSTPOSITIONS:
        clean = re.sub(pp, " ", clean, flags=re.IGNORECASE)
    clean = " ".join(clean.split())
    return clean


def clean_doctor_name(name: Optional[str]) -> str:
    """
    Normalize any variant of doctor name into clean 'Dr. <Name>'.
    Eliminates duplicated 'Dr. Dr', 'Doctor Dr', accidental trailing 'doctor/garu',
    conjunctions ('and', 'at', 'with', 'in'), and STT noise like 'new' suffix.
    """
    if not name:
        return ""
    s = str(name).strip()

    # 1. Strip trailing punctuation
    s = re.sub(r"[\.,;:!?]+$", "", s).strip()

    # 2. Remove trailing noise tokens like 'doctor', 'డాక్టర్', 'garu', 'gaaru', 'new', 'and', 'at', 'with', 'in'
    s = re.sub(r"\s+(?:doctor|డాక్టర్|గారు|garu|gaaru|new|and|at|with|in)$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\bnew\b", "", s, flags=re.IGNORECASE).strip()

    # 3. Collapse leading repeated titles: 'Dr.', 'Dr', 'Doctor', 'డాక్టర్', 'డా.', 'dr'
    s = re.sub(r"^(?:(?:dr\.?|doctor|డాక్టర్|డా\.?)\s*)+", "", s, flags=re.IGNORECASE).strip()

    # 4. Strip leading noise
    s = re.sub(r"^(?:a\s+new\s+|new\s+|a\s+|the\s+)", "", s, flags=re.IGNORECASE).strip()

    # 5. If nothing is left (e.g. input was just 'Dr Dr'), return empty
    if not s or s.lower() in ["dr", "dr.", "doctor", "the", "a", "and", "new", "doctor new"]:
        return ""

    # 6. Capitalize each word properly (unless already camel/mixed case)
    words = s.split()
    # Filter out lone conjunction words from the end
    if words and words[-1].lower() in ["and", "at", "with", "in", "whose", "his", "her"]:
        words = words[:-1]
    if not words:
        return ""

    capitalized = " ".join(
        w.capitalize() if not any(c.isupper() for c in w[1:]) else w
        for w in words
    )
    return f"Dr. {capitalized}"

