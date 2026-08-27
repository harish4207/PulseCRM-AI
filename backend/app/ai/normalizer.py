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


INVALID_PERSON_NAME_TOKENS = {
    # Temporal & Relative time
    "today", "tomorrow", "yesterday", "now", "soon", "morning", "evening", "afternoon", "night", "tonight",
    "repu", "ivala", "ninna", "ippude", "roju", "vaaram", "nela", "ee roju", "vachhe vaaram", "ganta", "nimisham",
    "next", "last", "chivari", "malli", "upcoming", "past",
    # Weekdays & Months
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "somavaram", "mangalavaram", "budhavaram", "guruvaram", "sukravaram", "sanivaram", "adivaram",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    # Pronouns & Determiners
    "someone", "somebody", "anyone", "anybody", "everyone", "everybody", "no one", "nobody", "person", "people",
    "him", "her", "them", "they", "he", "she", "it", "that", "this", "these", "those",
    "the", "a", "an", "whose", "his", "hers", "their", "theirs", "our", "ours", "my", "your",
    "aayana", "aavida", "ayana", "ame", "vaallu", "athadu", "aame", "athanu", "evaru", "evarini", "evaritho",
    # Generic CRM & Medical nouns / Actions
    "doctor", "physician", "hcp", "specialist", "surgeon", "cardiologist", "neurologist", "orthopedic",
    "hospital", "clinic", "care", "health", "center", "nursing", "home",
    "brochure", "samples", "sample", "catalog", "literature", "document", "file", "presentation", "deck",
    "meeting", "interaction", "visit", "call", "discussion", "appointment", "schedule", "followup", "follow-up", "follow up",
    "reminder", "alert", "notification", "note", "notes", "summary",
    "patient", "medicine", "drug", "product", "tablet", "syrup", "prescription", "rx",
    "new", "old", "recent", "kotha", "paatha", "save", "cancel", "confirm", "proceed", "edit", "change", "update",
    "create", "add", "log", "record", "details", "profile", "info", "brief", "briefing", "overview",
    # Telugu Verbs & Case Markers
    "kalisanu", "kalavali", "kalustha", "kalisa", "matladanu", "matladam", "matladaru", "adigaru", "adigindi",
    "pampali", "pampamani", "chesanu", "chesam", "ayindi", "kothaga", "vachanu", "cheppu", "kanipinchadu",
    "ni", "tho", "ki", "ga", "lo", "gaaru", "garu",
    "కలిశాను", "కలిసాను", "మాట్లాడాను", "అడిగారు", "అడిగింది", "కొత్త",
    # Product Names
    "cardiopress", "cardiopress-50", "cardiopress-75", "cardiopress-100", "amlopulse", "glycocare", "neurocalm", "lipidguard", "respiclear", "cancer medicine",
}


def is_valid_person_name(name: Optional[str]) -> bool:
    """
    Semantic Entity-Slot Validator:
    Validates that a string is a genuine person name and NOT a temporal word,
    pronoun, product, number, hospital, or generic CRM term.
    """
    if not name:
        return False
    s = str(name).strip()

    # Strip leading titles / noise
    s_clean = re.sub(r"^(?:(?:dr\.?|doctor|డాక్టర్|డా\.?|a\s+new\s+|new\s+|a\s+|the\s+)\s*)+", "", s, flags=re.IGNORECASE).strip()
    s_clean = re.sub(r"[\.,;:!?]+$", "", s_clean).strip()
    s_clean = re.sub(r"\s+(?:doctor|డాక్టర్|గారు|garu|gaaru|new|and|at|with|in)$", "", s_clean, flags=re.IGNORECASE).strip()

    if not s_clean or len(s_clean) < 2:
        return False

    lower_s = s_clean.lower()

    # Entire string blacklist check
    if lower_s in INVALID_PERSON_NAME_TOKENS:
        return False

    # Check for digit/time pattern
    if re.search(r"^\d+(?::\d+)?\s*(?:am|pm)?$", lower_s, re.IGNORECASE) or re.search(r"^\d+$", lower_s):
        return False

    # Check tokens
    words = [w for w in re.split(r"[\s\-_]+", lower_s) if w]
    if not words:
        return False

    # If single word is an invalid token, reject
    if len(words) == 1 and words[0] in INVALID_PERSON_NAME_TOKENS:
        return False

    # If all tokens are invalid tokens, reject (e.g. 'new today', 'tomorrow morning')
    if all(w in INVALID_PERSON_NAME_TOKENS for w in words):
        return False

    # Must contain at least one valid alphabetical token of length >= 2 that is NOT in the blacklist
    valid_name_tokens = [w for w in words if len(w) >= 2 and w not in INVALID_PERSON_NAME_TOKENS and re.search(r"[a-zA-Z\u0C00-\u0C7F]", w)]
    if not valid_name_tokens:
        return False

    return True


def clean_doctor_name(name: Optional[str]) -> str:
    """
    Normalize any variant of doctor name into clean 'Dr. <Name>'.
    Eliminates duplicated 'Dr. Dr', 'Doctor Dr', accidental trailing 'doctor/garu',
    conjunctions ('and', 'at', 'with', 'in'), and STT noise like 'new' suffix.
    Guarantees that non-person names (temporal words, pronouns, products) return empty string.
    """
    if not name or not is_valid_person_name(name):
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

    # 5. Semantic validity check
    if not is_valid_person_name(s):
        return ""

    # 6. Capitalize each word properly (unless already camel/mixed case)
    words = s.split()
    # Filter out lone conjunction words or temporal words from the end
    while words and words[-1].lower() in ["and", "at", "with", "in", "whose", "his", "her", "today", "tomorrow", "yesterday"]:
        words = words[:-1]

    # Filter out leading temporal words or pronouns
    while words and words[0].lower() in ["and", "at", "with", "in", "today", "tomorrow", "yesterday", "someone", "new", "her", "his", "him"]:
        words = words[1:]

    if not words:
        return ""

    capitalized = " ".join(
        w.capitalize() if not any(c.isupper() for c in w[1:]) else w
        for w in words
    )
    return f"Dr. {capitalized}"


