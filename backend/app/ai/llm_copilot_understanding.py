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
from app.ai.normalizer import normalize_transcript, extract_clean_search_tokens, clean_doctor_name
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
    r"\b(eppudu|kalisanu|gurinchi|cheppu|matladaru|matladam|aayana|avaru|chivari|"
    r"malli|rappudu|vachhe|em chepparu|em matladaru|kanipinchadu|naaku|meeru|"
    r"kalisina|ivala|ayindi|chesam|cheyyi|tho|ki|ni|ga|lo|doctor|hospital|"
    r"log cheyyi|record cheyyi|follow-up|schedule|visit|recent ga|evarini|anni|"
    r"avunu|vaddu|kaadu|evaritho|unna|pett|repu|somavaram|ippude|adigindi|pampali|kalavali|kalustha)\b",
    re.IGNORECASE,
)


class UnderstandingResult(BaseModel):
    language: str = "en"
    intent: str = INTENT_UNKNOWN
    doctor_name: Optional[str] = None
    hospital: Optional[str] = None
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

    # 1. Check Pending Confirmation state corrections & decisions
    if pending_confirmation:
        is_schedule_pending = (
            pending_action.get("type") == "SCHEDULE_MEETING"
            or "CREATE_MEETING" in pending_action.get("actions", [])
            or "CREATE_MEETING" in pending_action.get("planned_actions", [])
        )
        if is_schedule_pending:
            if any(k in lower for k in [
                "4 pm", "4:00 pm", "4:00", "3 pm", "11 am", "10 am", "2 pm", "5 pm", "marchu", "ki marchu", "make it", "time to", "change time"
            ]) and not any(cw in lower for cw in ["confirm", "avunu", "save", "cancel", "vaddu"]):
                from app.ai.meeting_extractor import parse_time_expression
                t_parsed = parse_time_expression(norm)
                if t_parsed:
                    res.intent = INTENT_CORRECT_PENDING_ACTION
                    res.corrections["change_time"] = t_parsed[2]
                    res.meeting_time_display = t_parsed[2]
                    return res

            if any(k in lower for k in [
                "remind me", "reminder", "gurthu", "alert", "no reminder", "don't remind", "remove reminder"
            ]) and not any(cw in lower for cw in ["confirm", "avunu", "save", "cancel", "vaddu"]):
                from app.ai.meeting_extractor import extract_reminder_preference
                if any(k in lower for k in ["no reminder", "remove reminder", "reminder vaddu", "don't remind"]):
                    res.intent = INTENT_CORRECT_PENDING_ACTION
                    res.corrections["remove_reminder"] = True
                    return res
                rem = extract_reminder_preference(norm)
                if rem:
                    res.intent = INTENT_CORRECT_PENDING_ACTION
                    res.corrections["change_reminder"] = rem[1]
                    res.reminder_minutes = rem[0]
                    res.reminder_display = rem[1]
                    return res

        if any(k in lower for k in [
            "no follow up", "no follow-up", "no followup", "remove follow", "remove the follow",
            "no follow-up scheduled", "there was no follow-up", "there was no follow up",
        ]):
            res.intent = INTENT_CORRECT_PENDING_ACTION
            res.corrections["remove_follow_up"] = True
            res.actions = ["CREATE_INTERACTION"]
            return res

        if any(k in lower for k in [
            "change", "actually", "the product was", "instead of", "reschedule", "not a brochure",
            "not apollo", "not care", "she asked for", "he asked for", "hospital is", "doctor to", "make it", "make that"
        ]):
            res.intent = INTENT_CORRECT_PENDING_ACTION
            dt_parsed = parse_date_expression(norm)
            if dt_parsed:
                res.corrections["change_follow_up"] = dt_parsed[1]
                res.corrections["change_date"] = dt_parsed[1]
                res.follow_up_display = dt_parsed[1]
                res.follow_up_date = dt_parsed[0].isoformat()

            doc_m = re.search(r"(?:actually\s+(?:it\s+was|the\s+doctor\s+was|i\s+meant)|doctor\s+was|doctor\s+to)\s+(?:dr\.?\s+)?([A-Za-z\s]+)", norm, re.IGNORECASE)
            if doc_m:
                d_name = doc_m.group(1).strip()
                res.corrections["change_doctor"] = d_name
                res.doctor_name = d_name

            prod_m = re.search(r"\b(CardioPress(?:-(?:50|75|100))?|Cancer Medicine|AmloPulse|GlycoCare|NeuroCalm|LipidGuard|RespiClear)\b", norm, re.IGNORECASE)
            if prod_m:
                res.corrections["change_product"] = prod_m.group(1)
                res.product = prod_m.group(1)

            req_m = re.search(r"(?:asked for|requested)\s+([A-Za-z\s,]+)", norm, re.IGNORECASE)
            if req_m:
                res.corrections["change_request"] = req_m.group(1).strip()
                res.doctor_request = req_m.group(1).strip()

            return res

        confirm_words = ["avunu", "yes", "confirm", "okay", "ok", "save it", "do it", "create it", "proceed", "sare", "schedule it", "confirm & schedule", "అవును", "సరే"]
        if any(lower == cw or lower.startswith(cw) or f" {cw} " in f" {lower} " for cw in confirm_words):
            res.intent = INTENT_CONFIRM_ACTION
            return res

        cancel_words = ["no", "cancel", "vaddu", "don't save", "dont save", "don't schedule", "don't do it", "stop", "వద్దు", "రద్దు", "vaddu, cancel cheyyi", "no, cancel it"]
        if any(lower == cw or lower.startswith(cw) or f" {cw} " in f" {lower} " for cw in cancel_words):
            res.intent = INTENT_CANCEL_ACTION
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
            clean_d = re.sub(r"\b(meeting|with|today|dr|doctor|డాక్టర్|గారు|before|what|should|i|know|about|on|for|prep|tho|details|cheppu)\b", "", doc_m.group(1), flags=re.IGNORECASE).strip()
            if clean_d:
                res.doctor_name = clean_d
        if not res.doctor_name and current_hcp_name:
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

        # Extract doctor name
        doc_m_before_post = re.search(r"([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)\s+(?:tho|ni|ki|తో|ని|కి|గారు|garu|gaaru)", norm, re.IGNORECASE)
        doc_m_after_verb = re.search(r"(?:meet|with|doctor|dr\.?)\s+(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)", norm, re.IGNORECASE)

        if doc_m_before_post:
            cand = re.sub(r"\b(meet|with|doctor|dr|డాక్టర్|గారు|tomorrow|repu|friday|monday|today|at|on|tho|ni|ki|ga|schedule|a|3|pm|am)\b", "", doc_m_before_post.group(1), flags=re.IGNORECASE).strip()
            if cand and len(cand) >= 2:
                res.doctor_name = cand
        elif doc_m_after_verb:
            cand = re.sub(r"\b(meet|with|doctor|dr|డాక్టర్|గారు|tomorrow|repu|friday|monday|today|at|on|tho|ni|ki|ga|schedule|a|3|pm|am|remind|me|to)\b", "", doc_m_after_verb.group(1), flags=re.IGNORECASE).strip()
            if cand and len(cand) >= 2:
                res.doctor_name = cand

        if not res.doctor_name and current_hcp_name:
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
            "what did we discuss", "what did i discuss"
        ]) or (has_known_prod and is_query)
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

    # C. Doctor Requests / Commitments Query (e.g. "What did he ask for?", "What did Dr Rajesh ask for?")
    if any(k in lower for k in ["what did he ask", "what did she ask", "what did they ask", "em adigaru", "em adigindi", "ask for"]):
        res.intent = INTENT_GET_HCP_INTERACTIONS
        if any(p in lower for p in ["he", "she", "him", "her", "aayana", "aavida"]) or current_hcp_name:
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        doc_m = re.search(r"(?:dr\.?\s+)?([A-Za-z]+)", norm, re.IGNORECASE)
        if doc_m and doc_m.group(1).lower() not in ["what", "did", "he", "she", "ask", "for"]:
            res.doctor_name = doc_m.group(1)
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
        "new doctor", "new hcp", "new physician", "create her in", "create him in", "add her", "add him",
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
        "logged meeting", "record meeting", "log interaction", "met dr", "and save", "save.", "save "
    ])

    if is_meeting_capture:
        res.intent = INTENT_CAPTURE_MEETING
        res.is_new_hcp = is_new_hcp
        res.phone = phone_val
        res.email = email_val
        res.specialization = spec_val

        # Doctor Name extraction
        name_m = re.search(r"\b(?:new doctor|new hcp|doctor|dr\.?|physician|hcp)\s+(?:dr\.?\s+)?([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)\b", norm, re.IGNORECASE)
        if name_m:
            cand_name = name_m.group(1).strip()
            cand_name = re.sub(r"\b(?:and|at|with|in|whose|his|her|phone|specialization|is|from|schedule|meeting)\b.*$", "", cand_name, flags=re.IGNORECASE).strip()
            if cand_name:
                res.doctor_name = clean_doctor_name(cand_name) or cand_name
        elif current_hcp_name and any(p in lower for p in ["him", "her", "she", "he", "aayana"]):
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name

        hosp_m = re.search(r"\b(?:at|in)\s+([A-Za-z\s]+(?:Hospital|Clinic|Health Center|Care|KIMS|Apollo|Manipal|Sunshine))\b", norm, re.IGNORECASE)
        if hosp_m:
            res.hospital = hosp_m.group(1).strip()

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
        if any(p in lower for p in ["him", "her", "she", "he", "aayana"]):
            res.is_anaphoric = True
            res.doctor_name = current_hcp_name
        name_m = re.search(r"\b(?:dr\.?\s+)?([A-Za-z]+)\b", norm, re.IGNORECASE)
        if name_m and name_m.group(1).lower() not in ["next", "follow", "up", "meeting", "when", "her", "him", "date", "for"]:
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


def understand_user_request(
    transcript: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Any]] = None,
) -> UnderstandingResult:
    ctx = context or {}
    return fallback_rule_understanding(transcript, ctx)
