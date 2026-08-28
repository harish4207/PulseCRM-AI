"""
llm_copilot_understanding.py - LLM-Powered Structured Understanding for Ask PulseCRM Copilot.

Uses Groq LLM (with resilient fallback) to extract intents, entities, actions, anaphora,
and multi-turn corrections from English, Telugu, and mixed code-switched speech.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.ai.agent import llm
from app.ai.normalizer import normalize_transcript, extract_clean_search_tokens, clean_doctor_name, is_valid_person_name
from app.ai.meeting_extractor import parse_date_expression, extract_request_action

logger = logging.getLogger(__name__)

# Core Intent Constants
INTENT_GET_HCP_DETAILS = "GET_HCP_DETAILS"
INTENT_SEARCH_HCP = "SEARCH_HCP"
INTENT_GET_HCP_INTERACTIONS = "GET_HCP_INTERACTIONS"
INTENT_GET_HCP_FOLLOWUPS = "GET_HCP_FOLLOWUPS"
INTENT_GET_ALL_FOLLOWUPS = "GET_ALL_FOLLOWUPS"
INTENT_GET_RECENT_INTERACTIONS = "GET_RECENT_INTERACTIONS"
INTENT_GET_PRODUCT_DISCUSSIONS = "GET_PRODUCT_DISCUSSIONS"
INTENT_GET_HOSPITAL_DETAILS = "GET_HOSPITAL_DETAILS"

INTENT_CAPTURE_MEETING = "CAPTURE_MEETING"
INTENT_SCHEDULE_MEETING = "SCHEDULE_MEETING"
INTENT_CREATE_HCP = "CREATE_HCP"
INTENT_CREATE_INTERACTION = "CREATE_INTERACTION"
INTENT_CREATE_FOLLOWUP = "CREATE_FOLLOWUP"
INTENT_GET_NEXT_ACTION = "GET_NEXT_ACTION"

INTENT_CONFIRM_ACTION = "CONFIRM_ACTION"
INTENT_CANCEL_ACTION = "CANCEL_ACTION"
INTENT_CORRECT_PENDING_ACTION = "CORRECT_PENDING_ACTION"

INTENT_GET_CRM_BRIEF = "GET_CRM_BRIEF"
INTENT_GET_PRE_MEETING_INTELLIGENCE = "GET_PRE_MEETING_INTELLIGENCE"
INTENT_GET_CRM_ANALYTICS = "GET_CRM_ANALYTICS"
INTENT_GENERAL_CRM_QUERY = "GENERAL_CRM_QUERY"
INTENT_UNKNOWN = "UNKNOWN"

TELUGU_UNICODE_RANGE = re.compile(r"[\u0C00-\u0C7F]")
TELUGU_LATIN_KEYWORDS = re.compile(
    r"\b(eppudu|kalisanu|gurinchi|cheppu|matladaru|matladam|aayana|aavida|avaru|chivari|"
    r"malli|rappudu|vachhe|em chepparu|em matladaru|kanipinchadu|naaku|meeru|"
    r"kalisina|ivala|ayindi|chesam|cheyyi|tho|ki|ni|ga|lo|"
    r"log cheyyi|record cheyyi|recent ga|evarini|anni|"
    r"avunu|vaddu|kaadu|evaritho|unna|pett|repu|somavaram|ippude|adigindi|pampali|kalavali|kalustha)\b",
    re.IGNORECASE,
)


class UnderstandingResult(BaseModel):
    language: str = "en"
    intent: str = INTENT_UNKNOWN
    doctor_name: Optional[str] = None
    doctors: List[str] = []
    hcp_entities: List[Dict[str, Any]] = []
    hospital: Optional[str] = None
    city: Optional[str] = None
    specialization: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    product: Optional[str] = None
    doctor_request: Optional[str] = None
    meeting_summary: Optional[str] = None
    follow_up_date: Optional[str] = None
    follow_up_display: Optional[str] = None
    meeting_time: Optional[str] = None
    meeting_time_display: Optional[str] = None
    reminder_minutes: Optional[int] = None
    reminder_display: Optional[str] = None
    location: Optional[str] = None
    time_filter: Optional[str] = None  # today, this_week, upcoming, all
    analytics_metric: Optional[str] = None  # weekly_meetings, overdue_followups, top_products, unvisited_doctors, hcps_without_followup
    is_new_hcp: bool = False
    is_anaphoric: bool = False
    anaphora_target: Optional[str] = None
    is_override: bool = False
    override_target: Optional[str] = None
    actions: List[str] = []
    confidence: float = 1.0
    corrections: Dict[str, Any] = {}
    conversational_reply: Optional[str] = None


def detect_language(text: str) -> str:
    if TELUGU_UNICODE_RANGE.search(text):
        return "te"
    if TELUGU_LATIN_KEYWORDS.search(text):
        return "mixed"
    return "en"


def fallback_rule_understanding(
    transcript: str,
    context: Dict[str, Any],
) -> UnderstandingResult:
    """
    High-precision deterministic understanding fallback.
    """
    raw = transcript.strip()
    norm = normalize_transcript(raw)
    lower = norm.lower()
    lang = detect_language(raw)

    pending_confirmation = context.get("pending_confirmation", False)
    pending_action = context.get("pending_action") or {}
    current_hcp_id = context.get("current_hcp_id")
    current_hcp_name = context.get("current_hcp_name")

    res = UnderstandingResult(language=lang)

    # 1. Check Pending Action / Confirmation state corrections & decisions
    has_pending = bool(pending_action) or pending_confirmation

    if has_pending:
        # Check for follow-up removal first (e.g. "No follow-up.", "There was no follow-up scheduled.")
        if any(k in lower for k in [
            "no follow up", "no follow-up", "no followup", "remove follow", "remove the follow",
            "no follow-up scheduled", "no followup scheduled", "there was no follow-up", "there was no follow up", "there was no followup"
        ]):
            res.intent = INTENT_CORRECT_PENDING_ACTION
            res.corrections["remove_follow_up"] = True
            res.actions = ["CREATE_INTERACTION"]
            return res

        # Check for explicit multi-turn corrections (e.g. "Change the doctor to Dr Ananya.", "Actually change the follow-up to October 1.", "Follow-up date change to November 5.")
        if any(k in lower for k in [
            "change", "actually", "the product was", "instead of", "reschedule", "not a brochure",
            "not apollo", "not care", "she asked for", "he asked for", "hospital is", "doctor to", "make it", "make that",
            "follow-up date change", "change the follow-up", "change the doctor", "change doctor"
        ]):
            res.intent = INTENT_CORRECT_PENDING_ACTION
            from app.ai.meeting_extractor import parse_time_expression, extract_reminder_preference
            t_parsed = parse_time_expression(norm)
            if t_parsed:
                res.corrections["change_time"] = t_parsed[2]
                res.meeting_time_display = t_parsed[2]

            if any(k in lower for k in ["no reminder", "remove reminder", "reminder vaddu", "don't remind", "dont remind", "i don't need the reminder"]):
                res.corrections["remove_reminder"] = True
                res.reminder_minutes = 0
                res.reminder_display = "No reminder"
            else:
                rem = extract_reminder_preference(norm)
                if rem:
                    res.corrections["change_reminder"] = rem[1]
                    res.reminder_minutes = rem[0]
                    res.reminder_display = rem[1]

            dt_parsed = parse_date_expression(norm)
            if dt_parsed:
                res.corrections["change_follow_up"] = dt_parsed[1]
                res.corrections["change_date"] = dt_parsed[1]
                res.follow_up_display = dt_parsed[1]
                res.follow_up_date = dt_parsed[0].isoformat()

            doc_m = re.search(r"(?:actually\s+(?:it\s+was|the\s+doctor\s+was|i\s+meant)|doctor\s+was|(?:change\s+(?:the\s+)?doctor\s+to)|doctor\s+to)\s+(?:dr\.?\s+)?([A-Za-z\s]+)", norm, re.IGNORECASE)
            if doc_m:
                d_name = doc_m.group(1).strip()
                if is_valid_person_name(d_name):
                    res.corrections["change_doctor"] = clean_doctor_name(d_name)
                    res.doctor_name = clean_doctor_name(d_name)

            prod_m = re.search(r"\b(CardioPress(?:-(?:50|75|100))?|Cancer Medicine|AmloPulse|GlycoCare|NeuroCalm|LipidGuard|RespiClear)\b", norm, re.IGNORECASE)
            if prod_m:
                res.corrections["change_product"] = prod_m.group(1)
                res.product = prod_m.group(1)

            req_m = re.search(r"(?:asked for|requested)\s+([A-Za-z\s,]+)", norm, re.IGNORECASE)
            if req_m:
                res.corrections["change_request"] = req_m.group(1).strip()
                res.doctor_request = req_m.group(1).strip()

            return res

        cancel_words = ["cancel", "vaddu", "don't save", "dont save", "don't schedule", "dont schedule", "don't do it", "dont do it", "stop", "వద్దు", "రద్దు", "vaddu, cancel cheyyi", "no, cancel it", "stop, don't do it"]
        is_exact_no = lower in ["no", "no.", "no!"] or (lower.startswith("no,") and "follow" not in lower)
        if is_exact_no or any(lower == cw or lower.startswith(cw) or f" {cw} " in f" {lower} " for cw in cancel_words):
            res.intent = INTENT_CANCEL_ACTION
            return res

        confirm_words = ["avunu", "yes", "confirm", "okay", "ok", "save it", "do it", "create it", "proceed", "sare", "schedule it", "confirm & schedule", "అవును", "సరే", "save everything", "okay save everything", "save all", "save.", "save", "confirm & save"]
        if any(lower == cw or lower.startswith(cw) or f" {cw} " in f" {lower} " for cw in confirm_words):
            res.intent = INTENT_CONFIRM_ACTION
            return res

        # Check for reminder modifications
        if any(k in lower for k in ["no reminder", "remove reminder", "reminder vaddu", "don't remind", "dont remind", "i don't need the reminder", "i dont need the reminder"]):
            res.intent = INTENT_CORRECT_PENDING_ACTION
            res.corrections["remove_reminder"] = True
            res.reminder_minutes = 0
            res.reminder_display = "No reminder"
            return res
        elif any(k in lower for k in ["remind me", "reminder", "gurthu", "alert", "one hour", "1 hour", "30 min", "minutes before"]):
            from app.ai.meeting_extractor import extract_reminder_preference
            rem = extract_reminder_preference(norm)
            if rem:
                res.intent = INTENT_CORRECT_PENDING_ACTION
                res.corrections["change_reminder"] = rem[1]
                res.reminder_minutes = rem[0]
                res.reminder_display = rem[1]
                return res

        # Check for time modifications (e.g. "Actually make it 4", "around four", "4:30", "at 4", "time to 4")
        if any(k in lower for k in ["make it", "make that", "change time", "time to", "actually", "around", "at 4", "at 3", "4 pm", "3 pm", "4:30", "4:", "3:", "pm", "am", "marchu"]):
            from app.ai.meeting_extractor import parse_time_expression
            t_parsed = parse_time_expression(norm)
            if t_parsed:
                res.intent = INTENT_CORRECT_PENDING_ACTION
                res.corrections["change_time"] = t_parsed[2]
                res.meeting_time_display = t_parsed[2]
                return res

        # Check for date modifications (e.g. "Actually Tuesday instead", "Next Wednesday", "Not tomorrow")
        if any(k in lower for k in ["instead", "next wednesday", "next tuesday", "next friday", "next monday", "wednesday", "tuesday", "friday", "monday", "repu", "tomorrow"]):
            dt_parsed = parse_date_expression(norm)
            if dt_parsed:
                res.intent = INTENT_CORRECT_PENDING_ACTION
                res.corrections["change_date"] = dt_parsed[1]
                res.corrections["change_follow_up"] = dt_parsed[1]
                res.follow_up_display = dt_parsed[1]
                res.follow_up_date = dt_parsed[0].isoformat()
                return res

        # Check for multi-attribute additions during an in-progress draft
        has_field_update = False

        # Doctor Name
        intro_m = re.search(r"\b(?:her|his|their|the|aayana|aavida|ayana|ame)?\s*(?:name|peru|పేరు)\s+(?:is|=|gaaru|garu|గారు)?\s*(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)
        called_m = re.search(r"\b(?:she's|shes|he's|hes|called|named|actually)\s+(?:called\s+|named\s+)?(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)
        d_cand = (intro_m.group(1).strip() if intro_m else None) or (called_m.group(1).strip() if called_m else None)
        if d_cand and is_valid_person_name(d_cand):
            res.doctor_name = clean_doctor_name(d_cand)
            res.corrections["change_doctor"] = res.doctor_name
            has_field_update = True

        # Specialization
        spec_m = re.search(r"\b(cardiologist|neurologist|orthopedic|oncologist|diabetologist|pediatrician|dermatologist|physician|surgeon)\b", norm, re.IGNORECASE)
        if spec_m:
            res.specialization = spec_m.group(1).capitalize()
            res.corrections["change_specialization"] = res.specialization
            has_field_update = True

        # Hospital
        hosp_m = re.search(r"\b(?:at|in|from)?\s*([A-Za-z0-9\s\-]*?(?:Hospital|Clinic|Health Center|Care|KIMS|Apollo|Manipal|Sunshine)(?:\s+(?:Hospital|Clinic|Hyderabad|Visakhapatnam|Vizag|Vijayawada|Bangalore|Chennai|Mumbai|Delhi))?)\b", norm, re.IGNORECASE)
        if hosp_m and len(hosp_m.group(1).strip()) >= 3:
            h_raw = hosp_m.group(1).strip()
            h_clean = re.sub(r"^(?:(?:she's|shes|he's|hes|i'm|im|she|he|a|the|is|at|in|from|works\s+at)\s+)+", "", h_raw, flags=re.IGNORECASE).strip()
            h_clean = re.sub(r"^(?:(?:cardiologist|neurologist|orthopedic|oncologist|physician|doctor|dr\.?)\s+(?:at|in|from)?\s*)+", "", h_clean, flags=re.IGNORECASE).strip()
            if h_clean and len(h_clean) >= 3:
                res.hospital = h_clean
                res.corrections["change_hospital"] = h_clean
                has_field_update = True

        # City
        city_m = re.search(r"\b(?:in|at)\s+(Hyderabad|Visakhapatnam|Vizag|Vijayawada|Bangalore|Chennai|Mumbai|Delhi|Guntur|Tirupati|Kurnool)\b", norm, re.IGNORECASE)
        if city_m:
            res.city = city_m.group(1).capitalize()
            res.corrections["change_city"] = res.city
            has_field_update = True

        # Phone
        phone_m = re.search(r"\b(?:mobile|phone|number|contact)?(?:\s+is)?\s*[:\s]?\s*(\d{7,15})\b", norm, re.IGNORECASE)
        if phone_m:
            res.phone = phone_m.group(1)
            res.corrections["change_phone"] = res.phone
            has_field_update = True

        # Product
        known_prods = ["CardioPress-50", "CardioPress-75", "CardioPress-100", "Cancer Medicine", "AmloPulse", "GlycoCare", "NeuroCalm", "LipidGuard", "RespiClear"]
        for p in known_prods:
            if p.lower() in lower:
                res.product = p
                res.corrections["change_product"] = p
                has_field_update = True
                break

        # Doctor Request
        req_val, _ = extract_request_action(norm)
        if req_val:
            res.doctor_request = req_val
            res.corrections["change_request"] = req_val
            has_field_update = True

        # Meeting / Schedule intent in draft
        if any(k in lower for k in ["let's meet", "lets meet", "let us meet", "meet next", "schedule a meeting", "schedule meeting", "see her", "see him", "kalavali"]):
            from app.ai.meeting_extractor import parse_time_expression
            res.intent = INTENT_SCHEDULE_MEETING
            t_p = parse_time_expression(norm)
            if t_p:
                res.meeting_time_display = t_p[2]
            d_p = parse_date_expression(norm)
            if d_p:
                res.follow_up_display = d_p[1]
                res.follow_up_date = d_p[0].isoformat()
            return res

        if has_field_update:
            res.intent = INTENT_CORRECT_PENDING_ACTION
            return res

    # 2. Check Context Override (e.g. "Rajesh kaadu Sharma doctor", "Not Rajesh, I meant Dr Sharma")
    override_m = re.search(r"(?:(\w+)\s+(?:kaadu|kadu|not)|not\s+(\w+)[,\.\s]+(?:i\s+meant\s+)?(?:dr\.?\s+)?)([A-Za-z\u0C00-\u0C7F\s]+)", raw, re.IGNORECASE)
    if override_m:
        target = override_m.group(3).strip()
        target = re.sub(r"\b(doctor|garu|డాక్టర్|gurinchi|cheppu|dr\.?)\b", "", target, flags=re.IGNORECASE).strip()
        if target:
            res.intent = INTENT_GET_HCP_DETAILS
            res.is_override = True
            res.override_target = target
            res.doctor_name = target
            return res

    # 3. Next Action Intelligence Check
    if any(k in lower for k in [
        "what should i do next", "what's the most important thing", "what is the most important thing",
        "what next", "next em cheyyali", "next action enti", "what do i need to do next", "most important action"
    ]):
        res.intent = INTENT_GET_NEXT_ACTION
        return res

    # 4. Advanced CRM Brief / "My Day" Checks
    if any(k in lower for k in [
        "what do i have today", "what's my day", "what is my day", "naaku ivala em undi", "today em schedule undi",
        "give me my day", "my day", "today's brief", "today briefing", "daily brief", "today's schedule brief",
        "ee roju schedule brief", "ee roju briefing", "today summary", "ee roju summary", "what does my day look like",
        "day overview", "morning brief", "crm brief", "give me today's brief", "plan for today", "plan today",
        "what is my plan", "my plan for today", "what's my plan for today", "today's plan"
    ]):
        res.intent = INTENT_GET_CRM_BRIEF
        return res

    # 5. Pre-Meeting Intelligence Check
    if any(k in lower for k in [
        "what should i know", "meeting briefing", "brief me on", "before meeting", "kalavabothunna",
        "details cheppu before meeting", "pre-meeting", "pre meeting", "info before meeting", "meeting mundu",
        "prep for"
    ]) or ("meeting" in lower and "what should i know" in lower):
        res.intent = INTENT_GET_PRE_MEETING_INTELLIGENCE
        doc_m = re.search(r"(?:meeting|with|about|on|for|dr\.?)\s+(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)
        if doc_m:
            clean_d = re.sub(r"\b(meeting|with|today|dr|doctor|డాక్టర్|గారు|before|what|should|i|know|about|on|for|prep|tho|details|cheppu|him|her|he|she|aayana|aavida)\b", "", doc_m.group(1), flags=re.IGNORECASE).strip()
            if clean_d:
                res.doctor_name = clean_d
        if (not res.doctor_name or any(p in lower for p in ["him", "her", "he", "she", "aayana", "aavida"])) and current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        return res

    # 6. CRM Analytics Check
    if any(k in lower for k in [
        "how many doctors", "how many meetings", "meetings completed", "doctors did i meet this week", "meet this week",
        "haven't i visited", "haven't visited", "not visited in", "not visited", "unvisited doctors", "unvisited",
        "products did i discuss most", "most discussed products", "top products", "follow-ups are overdue",
        "overdue follow-ups", "overdue followups", "how many follow-ups are overdue", "how many followups are overdue",
        "no upcoming follow-up", "no upcoming follow up", "weekly meetings", "meetings count", "doctors did i visit"
    ]):
        res.intent = INTENT_GET_CRM_ANALYTICS
        if any(w in lower for w in ["overdue"]):
            res.analytics_metric = "overdue_followups"
        elif any(w in lower for w in ["product", "most", "top"]):
            res.analytics_metric = "top_products"
        elif any(w in lower for w in ["haven't", "not visited", "unvisited"]):
            res.analytics_metric = "unvisited_doctors"
        elif any(w in lower for w in ["no upcoming"]):
            res.analytics_metric = "hcps_without_followup"
        else:
            res.analytics_metric = "weekly_meetings"
        return res

    # 7. Disambiguation: MEETING vs INTERACTION vs FOLLOW-UP
    is_explicit_save = any(s in lower for s in ["save this", "save it", "save cheyyi", "log this", "log meeting", "record meeting", "create her in", "create him in", "create new", "add her", "add him", "register new doctor", "and save", "save."])

    # A. Dedicated Meeting Scheduling (Future Calendar Meeting: "Meet Dr Rajesh Friday at 3 PM", "Meet Rajesh Friday", "Rajesh tho Friday 3 ki meeting pettu", "రాజేష్ డాక్టర్ ని శుక్రవారం 3 గంటలకు కలవాలి")
    is_meeting_scheduling = any(k in lower for k in [
        "meet dr", "meet rajesh", "meet priyanka", "meet sharma", "meet ananya", "meet suresh", "meet him", "meet her",
        "i want to meet", "want to meet", "meeting pettu", "meeting schedule cheyyi", "schedule a meeting",
        "schedule meeting with", "kalavali", "kalustha", "గంటలకు కలవాలి", "కలవాలి", "meeting pettali",
        "remind me to meet", "remind me to visit", "schedule meeting", "remind me to"
    ]) and not any(k in lower for k in ["i met", "just met", "kalisanu", "meeting ayindi", "last meeting", "chivari meeting", "when am i meeting", "when did i", "when was", "last meet", "eppudu kalisanu", "evarini kalavali"])

    if is_meeting_scheduling:
        from app.ai.meeting_extractor import extract_meeting_schedule_details
        res.intent = INTENT_SCHEDULE_MEETING
        details = extract_meeting_schedule_details(norm, current_hcp_id, current_hcp_name)
        res.meeting_time = details["meeting_time"]
        res.meeting_time_display = details["meeting_time_display"]
        res.follow_up_display = details["meeting_date_display"]
        res.reminder_minutes = details["reminder_minutes"]
        res.reminder_display = details["reminder_display"]
        res.location = details["location"]
        res.actions = details["planned_actions"]

        # Check for multiple doctors mentioned
        multi_m = re.findall(r"\b(?:dr\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", norm)
        stop_words = {
            "both", "and", "september", "october", "november", "december", "january", "february",
            "march", "april", "may", "june", "july", "august", "friday", "monday", "tuesday",
            "wednesday", "thursday", "saturday", "sunday", "tomorrow", "today", "yesterday",
            "doctor", "meeting", "schedule", "with", "at", "pm", "am", "remind", "me", "hospital"
        }
        valid_docs = [clean_doctor_name(d) for d in multi_m if is_valid_person_name(d) and d.lower() not in stop_words]
        if len(valid_docs) > 1:
            res.doctors = valid_docs
            res.doctor_name = valid_docs[0]
        else:
            # Extract single doctor name
            doc_m_before_post = re.search(r"([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)\s+(?:tho|ni|ki|తో|ని|కి|గారు|garu|gaaru)", norm, re.IGNORECASE)
            doc_m_after_verb = re.search(r"(?:meet|with|doctor|dr\.?)\s+(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)

            if doc_m_before_post:
                cand = re.sub(r"\b(meet|with|doctor|dr|డాక్టర్|గారు|tomorrow|repu|friday|monday|tuesday|wednesday|thursday|saturday|sunday|today|at|on|tho|ni|ki|ga|schedule|a|3|pm|am|remind|me|to|him|her|he|she|aayana|aavida|next)\b", "", doc_m_before_post.group(1), flags=re.IGNORECASE).strip()
                if cand and len(cand) >= 2:
                    res.doctor_name = cand
            elif doc_m_after_verb:
                cand = re.sub(r"\b(meet|with|doctor|dr|డాక్టర్|గారు|tomorrow|repu|friday|monday|tuesday|wednesday|thursday|saturday|sunday|today|at|on|tho|ni|ki|ga|schedule|a|3|pm|am|remind|me|to|him|her|he|she|aayana|aavida|next)\b", "", doc_m_after_verb.group(1), flags=re.IGNORECASE).strip()
                if cand and len(cand) >= 2:
                    res.doctor_name = cand

        if (not res.doctor_name or any(p in lower for p in ["him", "her", "he", "she", "aayana", "aavida"])) and current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        return res

    # B. Follow-up Action / Query (Task: "Follow up with Dr Rajesh next Friday", "follow-up schedule cheyyi")
    is_fu_command = (any(k in lower for k in [
        "follow up with", "follow-up with", "follow up next", "follow-up next", "follow up pettali",
        "follow-up schedule", "schedule a follow-up", "schedule follow-up", "schedule follow up", "create a follow-up", "create follow-up"
    ]) and not any(k in lower for k in ["na follow-ups", "all follow-ups", "what follow-ups"])
       and not is_explicit_save
       and not any(k in lower for k in ["just met", "i met", "met dr", "logged meeting"]))

    if is_fu_command:
        res.intent = INTENT_CREATE_FOLLOWUP
        dt_parsed = parse_date_expression(norm)
        if dt_parsed:
            res.follow_up_date = dt_parsed[0].isoformat()
            res.follow_up_display = dt_parsed[1]
        doc_m = re.search(r"(?:with|for|dr\.?)\s+(?:dr\.?\s+)?([A-Za-z]+)", norm, re.IGNORECASE)
        if doc_m and doc_m.group(1).lower() not in ["him", "her", "next", "friday", "monday"]:
            res.doctor_name = doc_m.group(1)
        elif current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        res.actions = ["CREATE_FOLLOWUP"]
        return res

    # 8. Questions vs Meeting Capture Commands
    is_query = any(q in lower for q in ["evarini", "evaritho", "evaru", "who", "which", "what", "list", "cheppu", "tell me", "show", "unna doctors", "anni", "when am i"]) and not is_explicit_save

    # A. Recent Interactions Query
    if any(k in lower for k in ["recent ga", "recently", "evarini kalisanu", "last week evarini", "recent interactions", "recent meetings", "who did i meet"]):
        res.intent = INTENT_GET_RECENT_INTERACTIONS
        return res

    # B. Product Discussions Query
    known_prods = ["CardioPress-50", "CardioPress-75", "CardioPress-100", "Cancer Medicine", "AmloPulse", "GlycoCare", "NeuroCalm", "LipidGuard", "RespiClear"]
    has_known_prod = any(p.lower() in lower for p in known_prods)
    is_prod_query = (
        any(k in lower for k in [
            "evaritho matladam", "which doctor", "who did i discuss", "evaritho discuss", "who did i present",
            "interested doctor", "which physicians", "discussion records", "adherence evaritho", "doctors tho meeting ayindi",
            "what did we discuss", "what did i discuss", "who did i talk", "who did i meet about", "discuss"
        ]) or (has_known_prod and (is_query or any(w in lower for w in ["who", "which", "discuss", "interested", "patients", "evaritho"])))
    ) and not is_explicit_save

    if is_prod_query:
        if has_known_prod:
            res.intent = INTENT_GET_PRODUCT_DISCUSSIONS
            for p in known_prods:
                if p.lower() in lower:
                    res.product = p
                    break
            return res
        elif current_hcp_name:
            res.intent = INTENT_GET_HCP_INTERACTIONS
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
            return res

    # C. Doctor Interactions / Requests / Commitments Query
    if any(k in lower for k in [
        "what did he ask", "what did she ask", "what did they ask", "em adigaru", "em adigindi", "ask for",
        "last interaction", "last meeting", "interacted with", "met with", "what was my last",
        "previous interaction", "previous meeting", "what did we discuss", "what did i discuss",
    ]):
        res.intent = INTENT_GET_HCP_INTERACTIONS
        if any(p in lower for p in ["he", "she", "him", "her", "aayana", "aavida", "ayana", "ame", "vaallu"]) or current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        doc_m = re.search(r"(?:dr\.?\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)", norm, re.IGNORECASE)
        if doc_m and is_valid_person_name(doc_m.group(1)):
            res.doctor_name = clean_doctor_name(doc_m.group(1))
        return res

    # D. When am I meeting him Query / Schedule query
    if any(k in lower for k in ["when am i meeting", "when is my meeting", "when do i meet"]):
        res.intent = INTENT_GET_HCP_FOLLOWUPS
        if current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        return res

    # E. All Follow-ups Query (Territory-wide)
    is_all_fu = any(k in lower for k in [
        "all follow-ups", "all followups", "all follow ups", "follow-ups anni", "followups anni", "follow ups anni",
        "na follow", "my follow-ups", "my followups", "what follow-ups", "what followups", "what follow ups",
        "upcoming follow", "scheduled follow", "schedule cheppandi", "visit this week", "doctors do i need to visit",
        "kalavalsina doctors", "today evaritho", "ivala nenu", "evarini kalavali", "upcoming doctor meetings",
        "today evaritho follow-up", "what follow-ups do i have", "which doctors do i need"
    ]) or (any(f in lower for f in ["follow-up", "followup", "follow up"]) and any(t in lower for t in ["today", "ivala", "this week", "next week", "anni", "all", "do i have"]))

    if is_all_fu and not is_explicit_save:
        res.intent = INTENT_GET_ALL_FOLLOWUPS
        if any(w in lower for w in ["today", "ivala", "ఈరోజు"]):
            res.time_filter = "today"
        elif any(w in lower for w in ["this week", "ee vaaram", "ఈ వారం"]):
            res.time_filter = "this_week"
        else:
            res.time_filter = "all"
        return res

    # F. Hospital Doctors Query
    if any(k in lower for k in ["doctors list", "unna doctors", "who is at", "doctors at", "who are the doctors", "lo evaru unnaru", "evaru unnaru"]):
        res.intent = INTENT_GET_HOSPITAL_DETAILS
        hosp_m = re.search(r"\b([A-Za-z\s]+(?:Hospital|Clinic|Care|KIMS|Apollo|Manipal|Sunshine))\b", norm, re.IGNORECASE)
        res.hospital = hosp_m.group(1).strip() if hosp_m else "Apollo Hospital"
        return res

    # 9. New HCP creation / Meeting Capture Commands
    is_new_hcp = any(k in lower for k in [
        "new doctor", "new hcp", "new physician", "someone new", "create her in", "create him in", "add her", "add him",
        "add new doctor", "add new hcp", "kotha doctor", "register new doctor", "create new doctor", "create new hcp"
    ])
    phone_m = re.search(r"\b(?:mobile|phone|number|contact)(?:\s+is)?\s*[:\s]?\s*(\d{7,15})\b", norm, re.IGNORECASE)
    phone_val = phone_m.group(1) if phone_m else None

    email_m = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", norm)
    email_val = email_m.group(1) if email_m else None

    spec_m = re.search(r"\b(?:specialization|speciality|specialist)(?:\s+is)?\s*[:\s]?\s*([A-Za-z\s]+)", norm, re.IGNORECASE)
    spec_val = spec_m.group(1).strip() if spec_m else None
    if spec_val:
        spec_val = re.sub(r"\b(?:and|at|with|in|is|her|his|phone|email)\b.*$", "", spec_val, flags=re.IGNORECASE).strip()

    is_meeting_capture = is_new_hcp or any(k in lower for k in [
        "just met", "i met", "had a meeting", "ippude kalisanu", "kalisanu", "meeting ayindi",
        "save this meeting", "save this", "save it", "save cheyyi", "log this meeting", "log cheyyi",
        "logged meeting", "record meeting", "log interaction", "met dr", "and save", "save.", "save ",
        "she's called", "shes called", "her name is", "his name is", "we talked about", "she wants"
    ])

    if is_meeting_capture:
        res.intent = INTENT_CAPTURE_MEETING
        res.is_new_hcp = is_new_hcp
        res.phone = phone_val
        res.email = email_val
        res.specialization = spec_val

        if not res.specialization:
            spec_match = re.search(r"\b(cardiologist|neurologist|orthopedic|oncologist|diabetologist|pediatrician|dermatologist|physician)\b", norm, re.IGNORECASE)
            if spec_match:
                res.specialization = spec_match.group(1).capitalize()

        # Doctor Name extraction with strict person validation
        cand_name = None
        name_m = re.search(r"\b(?:new doctor|new hcp|doctor|dr\.?|physician|hcp)\s+(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)\b", norm, re.IGNORECASE)
        if name_m:
            cand = name_m.group(1).strip()
            cand = re.sub(r"\b(?:and|at|with|in|whose|his|her|phone|specialization|is|from|schedule|meeting|today|tomorrow|yesterday|ni|tho|ki|ga|lo|kalisanu|matladanu|adigindi|adigaru)\b.*$", "", cand, flags=re.IGNORECASE).strip()
            if cand and is_valid_person_name(cand):
                cand_name = cand

        intro_m = re.search(r"\b(?:her|his|their|the|aayana|aavida|ayana|ame)?\s*(?:name|peru|పేరు)\s+(?:is|=|gaaru|garu|గారు)?\s*(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)
        if not cand_name and intro_m:
            cand = intro_m.group(1).strip()
            cand = re.sub(r"\b(?:and|at|with|in|whose|she|he|phone|specialization|is|from|ni|tho|ki|ga|lo)\b.*$", "", cand, flags=re.IGNORECASE).strip()
            if cand and is_valid_person_name(cand):
                cand_name = cand

        called_m = re.search(r"\b(?:she's|shes|he's|hes|called|named|actually|it was)\s+(?:called\s+|named\s+)?(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)
        if not cand_name and called_m:
            cand = called_m.group(1).strip()
            cand = re.sub(r"\b(?:and|at|with|in|whose|she|he|phone|specialization|is|from|today|tomorrow|yesterday|ni|tho|ki|ga|lo|kalisanu|matladanu|adigindi|adigaru)\b.*$", "", cand, flags=re.IGNORECASE).strip()
            if cand and is_valid_person_name(cand):
                cand_name = cand

        if cand_name and is_valid_person_name(cand_name):
            res.doctor_name = clean_doctor_name(cand_name)
        elif current_hcp_name and any(p in lower for p in ["him", "her", "she", "he", "aayana", "aavida"]):
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        else:
            res.doctor_name = None

        hosp_m = re.search(r"\b(?:at|in|from)\s+([A-Za-z0-9\s\-]*?(?:Hospital|Clinic|Health Center|Care|KIMS|Apollo|Manipal|Sunshine)(?:\s+(?:Hospital|Clinic|Hyderabad|Visakhapatnam|Vizag|Vijayawada|Bangalore|Chennai|Mumbai|Delhi))?)\b", norm, re.IGNORECASE)
        if hosp_m:
            res.hospital = hosp_m.group(1).strip()

        city_m = re.search(r"\b(?:in|at)\s+(Hyderabad|Visakhapatnam|Vizag|Vijayawada|Bangalore|Chennai|Mumbai|Delhi|Guntur|Tirupati|Kurnool)\b", norm, re.IGNORECASE)
        if city_m:
            res.city = city_m.group(1).capitalize()

        for p in known_prods:
            if p.lower() in lower:
                res.product = p
                break

        req_val, _ = extract_request_action(norm)
        res.doctor_request = req_val

        has_fu = any(k in lower for k in ["follow up", "follow-up", "followup", "schedule", "meet again", "pettali", "next friday", "next monday", "next month"]) or bool(re.search(r"\b(?:on)\s+(?:september|october|november|december|january)\b", lower))
        dt_parsed = parse_date_expression(norm) if has_fu else None
        if dt_parsed:
            res.follow_up_date = dt_parsed[0].isoformat()
            res.follow_up_display = dt_parsed[1]

        actions = []
        if is_new_hcp:
            actions.append("CREATE_HCP")
        actions.append("CREATE_INTERACTION")
        if res.follow_up_date:
            actions.append("CREATE_FOLLOWUP")
        res.actions = actions

        return res

    # 10. Single HCP follow-up Query
    if any(k in lower for k in ["next follow-up", "next followup", "next follow up", "next meeting", "malli eppudu", "follow-up eppudu", "follow-up date", "follow app"]):
        res.intent = INTENT_GET_HCP_FOLLOWUPS
        if any(p in lower for p in ["him", "her", "she", "he", "aayana", "aavida"]):
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        name_m = re.search(r"\b(?:dr\.?\s+)?([A-Za-z]+)\b", norm, re.IGNORECASE)
        if name_m and name_m.group(1).lower() not in ["next", "follow", "up", "meeting", "when", "her", "him", "he", "she", "aayana", "aavida", "eppudu", "date", "for"]:
            res.doctor_name = name_m.group(1)
        elif current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        return res

    # 11. Past Interactions Query
    if any(k in lower for k in ["last meeting", "chivari", "last time", "last meet", "last met", "when did i meet", "when did i last meet", "meet him last", "meet her last", "last time i met", "em matladam", "em matladaru", "em chepparu", "last see", "last visit", "last saw", "discuss with him", "discuss with her"]):
        res.intent = INTENT_GET_HCP_INTERACTIONS
        if any(p in lower for p in ["aayana", "him", "he", "she", "her", "doctor", "aavida"]):
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        doc_m = re.search(r"\b(?:dr\.?\s+)?([A-Za-z]+)\b", norm, re.IGNORECASE)
        if doc_m and doc_m.group(1).lower() not in ["when", "did", "i", "last", "meet", "met", "with", "him", "her", "last time"]:
            res.doctor_name = doc_m.group(1)
        elif current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        return res

    # 12. HCP Details / Profile Lookup Query
    if any(k in lower for k in ["gurinchi", "cheppu", "details", "tell me about", "who is", "profile", "doctor", "dr", "info", "specialization", "phone number", "hospital ekkada"]):
        res.intent = INTENT_GET_HCP_DETAILS
        if any(p in lower for p in ["aayana", "him", "he", "she", "her", "aavida"]):
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
            return res

        doc_m = re.search(r"(?:about|who is|dr\.?|doctor|for|profile of)\s+(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)
        if doc_m:
            cand = re.sub(r"\b(tell|me|about|who|is|doctor|dr|డాక్టర్|గారు|gurinchi|cheppu|details|profile|info)\b", "", doc_m.group(1), flags=re.IGNORECASE).strip()
            if cand:
                res.doctor_name = cand
                return res

        clean_text = extract_clean_search_tokens(norm)
        cand_words = [w for w in clean_text.split() if w.lower() not in ["tell", "me", "about", "who", "is", "doctor", "dr", "info", "details", "profile", "gurinchi", "cheppu"]]
        if cand_words:
            res.doctor_name = " ".join(cand_words)
        return res

    # 13. Short Name or Keyword Search
    clean_text = extract_clean_search_tokens(norm)
    tokens = clean_text.split()
    if len(tokens) >= 1 and len(norm.split()) <= 3:
        res.intent = INTENT_SEARCH_HCP
        res.doctor_name = clean_text
        return res

    res.intent = INTENT_GENERAL_CRM_QUERY
    return res


def llm_reasoning_understanding(
    transcript: str,
    context: Dict[str, Any],
    history: Optional[List[Any]] = None,
) -> Optional[UnderstandingResult]:
    """
    True LLM semantic reasoning and multi-turn slot extraction using Groq.
    """
    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY) < 10:
        return None

    try:
        from groq import Groq
        groq_client = Groq(api_key=settings.GROQ_API_KEY, timeout=4.0)

        ctx_summary = {
            "current_hcp_name": context.get("current_hcp_name"),
            "current_hospital": context.get("current_hospital"),
            "pending_confirmation": context.get("pending_confirmation", False),
            "pending_action": context.get("pending_action"),
        }

        hist_str = ""
        if history:
            hist_items = []
            for m in history[-6:]:
                role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else "user")
                content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else str(m))
                hist_items.append(f"{role.capitalize()}: {content}")
            hist_str = "\n".join(hist_items)

        sys_prompt = (
            "You are the intelligent reasoning core of Ask PulseCRM, an AI copilot for pharmaceutical sales reps in India.\n"
            "Analyze the user's message in the context of the conversation and evolving CRM state.\n"
            "Supported languages: English, Telugu (Telugu script or Latin transliteration), and mixed code-switching.\n\n"
            "Return a JSON object with these fields:\n"
            "- language: 'en' | 'te' | 'mixed'\n"
            "- intent: 'CAPTURE_MEETING' | 'SCHEDULE_MEETING' | 'CREATE_FOLLOWUP' | 'CONFIRM_ACTION' | 'CANCEL_ACTION' | 'CORRECT_PENDING_ACTION' | 'GET_HCP_DETAILS' | 'SEARCH_HCP' | 'GET_HCP_INTERACTIONS' | 'GET_HCP_FOLLOWUPS' | 'GET_ALL_FOLLOWUPS' | 'GET_RECENT_INTERACTIONS' | 'GET_PRODUCT_DISCUSSIONS' | 'GET_HOSPITAL_DETAILS' | 'GET_CRM_BRIEF' | 'GET_PRE_MEETING_INTELLIGENCE' | 'GET_CRM_ANALYTICS' | 'GET_NEXT_ACTION' | 'GENERAL_CRM_QUERY'\n"
            "- doctor_name: Real person name only (e.g. 'Dr. Ananya Rao'). NEVER 'today', 'tomorrow', 'yesterday', verbs, or temporal words.\n"
            "- hospital: Hospital or clinic name (e.g. 'KIMS Hospital') or null\n"
            "- city: City name (e.g. 'Hyderabad') or null\n"
            "- specialization: Medical specialty (e.g. 'Cardiologist') or null\n"
            "- phone: Phone number or null\n"
            "- email: Email or null\n"
            "- product: Pharma product name or null\n"
            "- doctor_request: Samples or brochure requested or null\n"
            "- follow_up_display: Follow-up date string or null\n"
            "- meeting_time_display: Meeting time string or null\n"
            "- reminder_display: Reminder string or null\n"
            "- reminder_minutes: integer offset in minutes or null\n"
            "- is_new_hcp: boolean\n"
            "- is_anaphoric: boolean (true if referencing current doctor via him/her/aayana/aavida)\n"
            "- corrections: object with modified slots if correcting a pending draft\n"
            "- conversational_reply: Direct, helpful, grounded assistant answer in the appropriate language (Telugu/English) if answering a question or general conversation.\n\n"
            "CRITICAL:\n"
            "1. Temporal words like 'today', 'tomorrow' must NEVER be doctor_name.\n"
            "2. If user mentions meeting a doctor but no name is provided, leave doctor_name as null.\n"
        )

        user_content = f"Conversation History:\n{hist_str}\n\nCurrent CRM Context:\n{json.dumps(ctx_summary)}\n\nLatest User Message:\n\"{transcript}\""

        chat_completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        raw_json = chat_completion.choices[0].message.content
        data = json.loads(raw_json)

        res = UnderstandingResult(
            language=data.get("language") or detect_language(transcript),
            intent=data.get("intent") or INTENT_GENERAL_CRM_QUERY,
            doctor_name=data.get("doctor_name"),
            doctors=data.get("doctors") or [],
            hcp_entities=data.get("hcp_entities") or [],
            hospital=data.get("hospital"),
            city=data.get("city"),
            specialization=data.get("specialization"),
            phone=data.get("phone"),
            email=data.get("email"),
            product=data.get("product"),
            doctor_request=data.get("doctor_request"),
            follow_up_display=data.get("follow_up_display"),
            meeting_time_display=data.get("meeting_time_display"),
            reminder_display=data.get("reminder_display"),
            reminder_minutes=data.get("reminder_minutes"),
            is_new_hcp=bool(data.get("is_new_hcp")),
            is_anaphoric=bool(data.get("is_anaphoric")),
            corrections=data.get("corrections") or {},
            conversational_reply=data.get("conversational_reply"),
            confidence=0.95,
        )

        if res.doctor_name:
            if not is_valid_person_name(res.doctor_name):
                res.doctor_name = None
            else:
                res.doctor_name = clean_doctor_name(res.doctor_name)

        return res

    except Exception as e:
        logger.warning(f"[LLM Understanding] Live LLM call failed or skipped: {e}")
        return None


def understand_user_request(
    transcript: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Any]] = None,
    preferred_provider: Optional[str] = None,
) -> UnderstandingResult:
    """
    Unified entrypoint for user understanding, routing through ReasoningEngine.
    """
    ctx = context or {}
    from app.ai.reasoning_engine import reasoning_engine

    r = reasoning_engine.reason(
        transcript=transcript,
        context=ctx,
        history=history,
        preferred_provider=preferred_provider,
    )

    res = UnderstandingResult(
        language=r.language,
        intent=r.intent,
        doctor_name=r.doctor_name,
        doctors=r.doctors,
        hcp_entities=r.hcp_entities,
        hospital=r.hospital,
        city=r.city,
        specialization=r.specialization,
        phone=r.phone,
        email=r.email,
        product=r.product,
        doctor_request=r.doctor_request,
        meeting_summary=r.meeting_summary,
        follow_up_date=r.follow_up_date,
        follow_up_display=r.follow_up_display,
        meeting_time=r.meeting_time,
        meeting_time_display=r.meeting_time_display,
        reminder_minutes=r.reminder_minutes,
        reminder_display=r.reminder_display,
        location=r.location,
        is_new_hcp=r.is_new_hcp,
        is_anaphoric=r.is_anaphoric,
        is_override=r.is_override,
        override_target=r.override_target,
        actions=r.actions,
        corrections=r.corrections,
        conversational_reply=r.conversational_reply,
        confidence=r.confidence,
    )

    return res
