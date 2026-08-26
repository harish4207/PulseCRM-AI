import re
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Set

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from app.config.settings import settings
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.ai.normalizer import normalize_transcript, extract_clean_search_tokens
from app.ai.fuzzy_matcher import (
    normalize_text,
    match_hcp_from_db,
    match_hospital_from_db,
    match_product_from_transcript,
    calculate_similarity,
)
from app.ai.meeting_extractor import (
    parse_date_expression,
    extract_request_action,
    apply_meeting_correction,
)
from app.ai.llm_copilot_understanding import (
    understand_user_request,
    UnderstandingResult,
    INTENT_GET_HCP_DETAILS,
    INTENT_SEARCH_HCP,
    INTENT_GET_HCP_INTERACTIONS,
    INTENT_GET_HCP_FOLLOWUPS,
    INTENT_GET_ALL_FOLLOWUPS,
    INTENT_GET_RECENT_INTERACTIONS,
    INTENT_GET_PRODUCT_DISCUSSIONS,
    INTENT_GET_HOSPITAL_DETAILS,
    INTENT_CAPTURE_MEETING,
    INTENT_SCHEDULE_MEETING,
    INTENT_CREATE_HCP,
    INTENT_CREATE_INTERACTION,
    INTENT_CREATE_FOLLOWUP,
    INTENT_GET_NEXT_ACTION,
    INTENT_CONFIRM_ACTION,
    INTENT_CANCEL_ACTION,
    INTENT_CORRECT_PENDING_ACTION,
    INTENT_GET_CRM_BRIEF,
    INTENT_GET_PRE_MEETING_INTELLIGENCE,
    INTENT_GET_CRM_ANALYTICS,
    INTENT_GENERAL_CRM_QUERY,
    INTENT_UNKNOWN,
)
from app.ai.meeting_extractor import (
    parse_date_expression,
    extract_request_action,
    apply_meeting_correction,
    apply_meeting_schedule_correction,
    extract_meeting_schedule_details,
)
from app.ai.voice_tools import (
    search_hcps,
    get_hcp_details,
    get_hcp_interactions,
    get_hcp_followups,
    get_all_followups,
    get_recent_interactions,
    get_product_discussions,
    get_hospital_doctors,
    search_interactions,
    create_hcp,
    create_interaction,
    create_followup,
    get_crm_day_brief,
    get_pre_meeting_intelligence,
    get_crm_analytics,
    schedule_meeting,
    check_meeting_conflict,
    get_next_action,
    get_scheduled_meetings,
)
from app.ai.voice_tools import (
    search_hcps,
    get_hcp_details,
    get_hcp_interactions,
    get_hcp_followups,
    get_all_followups,
    get_recent_interactions,
    get_product_discussions,
    get_hospital_doctors,
    search_interactions,
    create_hcp,
    create_interaction,
    create_followup,
    get_crm_day_brief,
    get_pre_meeting_intelligence,
    get_crm_analytics,
)

logger = logging.getLogger(__name__)

EXECUTED_ACTION_IDS: Set[str] = set()

class VoiceCopilotState(BaseModel):
    user_id: int
    transcript: str
    normalized_transcript: str = ""
    history: List[Dict[str, str]] = []

    current_hcp_id: Optional[int] = None
    current_hcp_name: Optional[str] = None
    current_hospital: Optional[str] = None
    current_topic: Optional[str] = None
    last_intent: Optional[str] = None
    last_tool: Optional[str] = None

    pending_confirmation: bool = False
    pending_action: Optional[Dict[str, Any]] = None

    understanding: Optional[UnderstandingResult] = None
    language: str = "en"
    intent: str = INTENT_UNKNOWN
    entity_name: Optional[str] = None
    entity_hospital: Optional[str] = None
    entity_product: Optional[str] = None
    is_anaphoric: bool = False
    is_override: bool = False
    override_target: Optional[str] = None

    resolved_hcp: Optional[Dict[str, Any]] = None
    ambiguous_candidates: List[Dict[str, Any]] = []
    confidence: float = 1.0
    needs_clarification: bool = False
    clarification_type: Optional[str] = None

    tool_result: Optional[Dict[str, Any]] = None
    card_data: Optional[Dict[str, Any]] = None
    response: str = ""
    error: Optional[str] = None

_CURRENT_DB = None

def normalize_input(state: VoiceCopilotState) -> dict:
    norm = normalize_transcript(state.transcript)
    return {"normalized_transcript": norm}


def llm_understand(state: VoiceCopilotState) -> dict:
    ctx = {
        "current_hcp_id": state.current_hcp_id,
        "current_hcp_name": state.current_hcp_name,
        "current_hospital": state.current_hospital,
        "pending_confirmation": state.pending_confirmation,
        "pending_action": state.pending_action,
    }

    und = understand_user_request(
        transcript=state.normalized_transcript or state.transcript,
        context=ctx,
        history=state.history,
    )

    return {
        "understanding": und,
        "language": und.language,
        "intent": und.intent,
        "entity_name": und.doctor_name,
        "entity_hospital": und.hospital,
        "entity_product": und.product,
        "is_anaphoric": und.is_anaphoric,
        "is_override": und.is_override,
        "override_target": und.override_target,
        "confidence": und.confidence,
    }


def resolve_entities(state: VoiceCopilotState) -> dict:
    global _CURRENT_DB
    db = _CURRENT_DB
    und = state.understanding
    from app.ai.normalizer import clean_doctor_name

    # Skip DB resolution for confirmation/cancellation/all follow-ups/briefing/analytics
    if state.intent in [
        INTENT_CONFIRM_ACTION,
        INTENT_CANCEL_ACTION,
        INTENT_CORRECT_PENDING_ACTION,
        INTENT_GET_ALL_FOLLOWUPS,
        INTENT_GET_RECENT_INTERACTIONS,
        INTENT_GET_CRM_BRIEF,
        INTENT_GET_CRM_ANALYTICS,
        INTENT_GET_NEXT_ACTION,
    ]:
        return {}

    # 1. Handle Override (e.g. "Rajesh kaadu Sharma doctor", "Not Rajesh, I meant Sharma")
    if state.is_override and state.override_target:
        raw_target = state.override_target
        clean_target = clean_doctor_name(raw_target) or raw_target
        match_result = match_hcp_from_db(db, clean_target)
        if match_result.get("best_match"):
            best = match_result["best_match"]
            return {
                "resolved_hcp": best,
                "current_hcp_id": best["id"],
                "current_hcp_name": best["doctor_name"],
                "current_hospital": best.get("hospital"),
                "is_anaphoric": False,
            }
        return {
            "resolved_hcp": None,
            "current_hcp_id": None,
            "current_hcp_name": clean_target,
            "is_anaphoric": False,
        }

    # 2. Handle Anaphoric reference (e.g. "Aayana last meeting eppudu?", "When did I meet him?", "What did we discuss?")
    if (state.is_anaphoric or (und and und.is_anaphoric)):
        hcp = None
        if state.current_hcp_id:
            hcp = get_hcp_details(db, state.current_hcp_id)
        if not hcp and state.current_hcp_name:
            match_res = match_hcp_from_db(db, state.current_hcp_name)
            hcp = match_res.get("best_match")
        if hcp:
            return {
                "resolved_hcp": hcp,
                "current_hcp_id": hcp["id"],
                "current_hcp_name": hcp["doctor_name"],
                "current_hospital": hcp.get("hospital"),
                "confidence": 1.0,
                "needs_clarification": False,
            }
        elif state.current_hcp_name:
            return {
                "resolved_hcp": None,
                "current_hcp_id": state.current_hcp_id,
                "current_hcp_name": state.current_hcp_name,
                "confidence": 1.0,
                "needs_clarification": False,
            }

    # 3. Always search DB first for doctor query (Exact, Normalized, Fuzzy, Phonetic, Transliteration)
    query_text = (und.doctor_name if und and und.doctor_name else None) or state.entity_name or state.normalized_transcript or state.transcript
    match_result = match_hcp_from_db(db, query_text)

    best_match = match_result.get("best_match")
    is_ambiguous = match_result.get("is_ambiguous", False)
    candidates = match_result.get("candidates", [])
    confidence = match_result.get("confidence", 0.0)

    if is_ambiguous and len(candidates) > 1:
        return {
            "ambiguous_candidates": candidates,
            "needs_clarification": True,
            "clarification_type": "ambiguity",
            "confidence": 0.5,
        }

    if best_match and confidence >= 0.65:
        return {
            "resolved_hcp": best_match,
            "current_hcp_id": best_match["id"],
            "current_hcp_name": best_match["doctor_name"],
            "current_hospital": best_match.get("hospital"),
            "confidence": confidence,
            "needs_clarification": False,
        }

    # 4. Handle Explicit New HCP Creation Request (e.g. "I met a new doctor Dr Sheila", "add new doctor")
    if und and und.is_new_hcp:
        new_doc_name = clean_doctor_name(und.doctor_name or state.entity_name or "New Doctor")
        return {
            "resolved_hcp": {
                "id": None,
                "doctor_name": new_doc_name,
                "hospital": und.hospital or "General Hospital",
                "specialization": und.specialization or "General Medicine",
                "phone": und.phone,
                "email": und.email,
                "is_new": True,
            },
            "confidence": 0.95,
            "needs_clarification": False,
        }

    return {"resolved_hcp": None, "confidence": 0.4, "needs_clarification": False}


def plan_actions_and_review(state: VoiceCopilotState) -> dict:
    global _CURRENT_DB
    db = _CURRENT_DB
    intent = state.intent
    und = state.understanding
    is_te = state.language in ["te", "mixed"]
    from app.ai.normalizer import clean_doctor_name

    if state.needs_clarification and state.clarification_type == "ambiguity":
        return {}

    # 1. Handle Schedule Meeting Planning (Future Calendar Meeting)
    if intent == INTENT_SCHEDULE_MEETING:
        target_hcp = state.resolved_hcp
        if not target_hcp and und and und.doctor_name:
            match_res = match_hcp_from_db(db, und.doctor_name)
            if match_res.get("best_match"):
                target_hcp = match_res["best_match"]
        if not target_hcp and state.current_hcp_id:
            hcp_rec = get_hcp_details(db, state.current_hcp_id)
            if hcp_rec:
                target_hcp = hcp_rec
        if not target_hcp and state.current_hcp_name:
            match_res = match_hcp_from_db(db, state.current_hcp_name)
            if match_res.get("best_match"):
                target_hcp = match_res["best_match"]
            else:
                target_hcp = {
                    "id": state.current_hcp_id or 1,
                    "doctor_name": state.current_hcp_name,
                    "hospital": state.current_hospital or "Apollo Hospital",
                    "city": "Visakhapatnam",
                    "specialization": "Cardiologist",
                }

        if not target_hcp:
            cand_name = clean_doctor_name((und.doctor_name if und else None) or state.entity_name or "the doctor")
            prompt = (
                f"డాక్టర్ '{cand_name or 'డాక్టర్'}' CRM లో కనుగొనబడలేదు. కొత్త HCP గా add చేయమంటారా?"
                if is_te
                else f"I couldn't find '{cand_name or 'the doctor'}' in your HCP directory. Would you like me to add them as a new doctor?"
            )
            return {"needs_clarification": True, "clarification_type": "hcp_not_found", "response": prompt}

        doc_name = clean_doctor_name(target_hcp.get("doctor_name")) or "Doctor"
        hosp = target_hcp.get("hospital") or "Apollo Hospital"
        city = target_hcp.get("city") or ""
        spec = target_hcp.get("specialization") or ""
        hcp_id = target_hcp.get("id", 1)

        dt_disp = (und.follow_up_display if und and und.follow_up_display else None) or "Friday"
        tm_disp = (und.meeting_time_display if und and und.meeting_time_display else None) or "03:00 PM"
        m_time_iso = und.meeting_time if und else None
        if not m_time_iso:
            now = datetime.now()
            days = (4 - now.weekday() + 7) % 7
            days = 7 if days == 0 else days
            m_time_iso = (now + timedelta(days=days)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()

        # Check duplicate / conflict
        try:
            dt_obj = datetime.fromisoformat(m_time_iso)
            conflict_info = check_meeting_conflict(db, user_id=state.user_id, target_time=dt_obj, hcp_id=hcp_id)
        except Exception:
            conflict_info = {"is_duplicate": False, "is_conflict": False}

        action_id = str(uuid.uuid4())[:8]
        rem_disp = (und.reminder_display if und and und.reminder_display else None) or "30 minutes before"
        rem_min = (und.reminder_minutes if und and und.reminder_minutes else None) or 30
        loc_str = f"{hosp} · {city}" if city and city.lower() not in hosp.lower() else hosp

        pending_action = {
            "action_id": action_id,
            "type": "SCHEDULE_MEETING",
            "hcp_id": hcp_id,
            "hcp_name": doc_name,
            "hospital": hosp,
            "city": city,
            "specialization": spec,
            "meeting_time": m_time_iso,
            "meeting_date_display": dt_disp,
            "meeting_time_display": tm_disp,
            "location": loc_str,
            "reminder_display": rem_disp,
            "reminder_minutes": rem_min,
            "actions": ["CREATE_MEETING", "CREATE_REMINDER"] if rem_disp else ["CREATE_MEETING"],
            "conflict_info": conflict_info,
        }

        rem_s_en = f" (with a {rem_disp} reminder)" if rem_disp and rem_disp.lower() not in ["none", "no reminder"] else ""
        rem_s_te = f" ({rem_disp} reminder తో)" if rem_disp and rem_disp.lower() not in ["none", "no reminder"] else ""

        if is_te:
            conf_msg = f"{doc_name} ({hosp}) తో {dt_disp} {tm_disp} కి మీటింగ్ వివరాలు సిద్ధం చేశాను{rem_s_te}. దయచేసి సమీక్షించి ధృవీకరించండి."
        else:
            conf_msg = f"Here is the meeting review for {doc_name} at {hosp} on {dt_disp} at {tm_disp}{rem_s_en}. Please review and confirm to schedule."

        card_data = {
            "type": "meeting_schedule_confirmation",
            "action_id": action_id,
            "doctor_name": doc_name,
            "hospital": hosp,
            "city": city,
            "specialization": spec,
            "meeting_date_display": dt_disp,
            "meeting_time_display": tm_disp,
            "location": loc_str,
            "reminder_display": rem_disp or "No reminder",
            "actions": pending_action["actions"],
            "conflict_info": conflict_info,
        }

        return {
            "pending_confirmation": True,
            "pending_action": pending_action,
            "card_data": card_data,
            "response": conf_msg,
            "current_hcp_id": hcp_id,
            "current_hcp_name": doc_name,
            "current_hospital": hosp,
        }

    # 2. Handle Natural Language Correction on Pending Proposal
    if intent == INTENT_CORRECT_PENDING_ACTION and state.pending_action:
        db_hcps = db.query(HCP).all() if db else []
        p_type = state.pending_action.get("type")

        if p_type == "SCHEDULE_MEETING":
            updated_action, changes = apply_meeting_schedule_correction(
                state.pending_action, state.normalized_transcript or state.transcript, db_hcps=db_hcps
            )
            doc_name = clean_doctor_name(updated_action.get("hcp_name")) or "Doctor"
            hosp = updated_action.get("hospital", "")
            dt_disp = updated_action.get("meeting_date_display", "Date")
            tm_disp = updated_action.get("meeting_time_display", "Time")
            rem_disp = updated_action.get("reminder_display") or "No reminder"
            change_summary = ", ".join(changes) if changes else "Updated details"

            if is_te:
                conf_msg = f"మీటింగ్ వివరాలు సవరించాను ({change_summary}). ధృవీకరించి షెడ్యూల్ చేయమంటారా?"
            else:
                conf_msg = f"I've updated the meeting review with your changes ({change_summary}). Please confirm to schedule."

            card_data = {
                "type": "meeting_schedule_confirmation",
                "action_id": updated_action.get("action_id"),
                "doctor_name": doc_name,
                "hospital": hosp,
                "meeting_date_display": dt_disp,
                "meeting_time_display": tm_disp,
                "location": updated_action.get("location"),
                "reminder_display": updated_action.get("reminder_display") or "No reminder",
                "actions": updated_action.get("actions", []),
                "changes_applied": changes,
            }
            return {
                "pending_confirmation": True,
                "pending_action": updated_action,
                "card_data": card_data,
                "response": conf_msg,
                "current_hcp_id": updated_action.get("hcp_id"),
                "current_hcp_name": doc_name,
                "current_hospital": hosp,
            }

        # Meeting capture correction
        updated_action, changes = apply_meeting_correction(state.pending_action, state.transcript, db_hcps=db_hcps)

        doc_name = clean_doctor_name(updated_action.get("hcp_name")) or "Doctor"
        hosp = updated_action.get("hospital", "")
        prod = updated_action.get("products_discussed") or None
        req = updated_action.get("request") or None
        fu_disp = updated_action.get("follow_up_display") or None
        actions = updated_action.get("actions", ["CREATE_INTERACTION"])

        change_summary = ", ".join(changes) if changes else "Updated details"

        if is_te:
            conf_msg = f"వివరాలు సవరించాను ({change_summary}). Interaction ని సేవ్ చేయమంటారా?"
        else:
            conf_msg = f"I've updated the meeting review with your changes ({change_summary}). Please confirm to save."

        return {
            "pending_confirmation": True,
            "pending_action": updated_action,
            "current_hcp_id": updated_action.get("hcp_id"),
            "current_hcp_name": doc_name,
            "current_hospital": hosp,
            "response": conf_msg,
            "card_data": {
                "type": "meeting_capture_confirmation",
                "action_id": updated_action.get("action_id"),
                "doctor_name": doc_name,
                "hospital": hosp,
                "phone": updated_action.get("phone") or "Not specified",
                "email": updated_action.get("email") or "Not specified",
                "product": prod or "Not specified",
                "request": req or "Not specified",
                "follow_up": fu_disp or "Not scheduled",
                "actions": actions,
                "is_new_hcp": updated_action.get("is_new_hcp", False),
            },
        }

    # Handle Meeting Capture / New HCP Review Proposal
    if intent in [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP]:
        # If doctor not found and not a new HCP creation request, ask whether to add
        if not state.resolved_hcp and not (und and und.is_new_hcp):
            cand_name = clean_doctor_name(state.entity_name or "the doctor")
            prompt = (
                f"డాక్టర్ '{cand_name or 'డాక్టర్'}' CRM లో కనుగొనబడలేదు. కొత్త HCP గా add చేయమంటారా?"
                if is_te
                else f"I couldn't find '{cand_name or 'the doctor'}' in your HCP directory. Would you like me to add them as a new doctor?"
            )
            return {"needs_clarification": True, "clarification_type": "hcp_not_found", "response": prompt}

        # Build Planned Action Payload
        hcp_info = state.resolved_hcp or {}
        raw_name = hcp_info.get("doctor_name") or (und.doctor_name if und else None) or "Doctor"
        doc_name = clean_doctor_name(raw_name) or "Doctor"
        hosp = hcp_info.get("hospital") or (und.hospital if und else None) or "General Hospital"
        spec = hcp_info.get("specialization") or (und.specialization if und else None) or "General Medicine"
        phone = hcp_info.get("phone") or (und.phone if und else None)
        email = hcp_info.get("email") or (und.email if und else None)

        prod_val = (und.product if und and und.product and und.product != "General discussion" else None)
        req_str = und.doctor_request if und and und.doctor_request and und.doctor_request != "None" else None
        fu_disp = und.follow_up_display if und else None
        fu_iso = und.follow_up_date if und else None

        actions = (und.actions if und and und.actions else None) or (["CREATE_INTERACTION", "CREATE_FOLLOWUP"] if fu_disp else ["CREATE_INTERACTION"])
        if hcp_info.get("is_new") or (und and und.is_new_hcp):
            if "CREATE_HCP" not in actions:
                actions.insert(0, "CREATE_HCP")

        evidence = {}
        if req_str:
            evidence["request"] = req_str
        if fu_disp:
            evidence["follow_up"] = fu_disp

        notes_p = [f"Meeting with {doc_name} at {hosp}."]
        if prod_val:
            notes_p.append(f"Discussed product: {prod_val}.")
        if req_str:
            notes_p.append(f"Doctor request: {req_str}.")
        if fu_disp:
            notes_p.append(f"Follow-up scheduled for {fu_disp}.")

        pending_action = {
            "action_id": str(uuid.uuid4())[:8],
            "type": INTENT_CAPTURE_MEETING,
            "is_new_hcp": bool(hcp_info.get("is_new") or (und and und.is_new_hcp)),
            "hcp_id": hcp_info.get("id"),
            "hcp_name": doc_name,
            "hospital": hosp,
            "specialization": spec,
            "phone": phone,
            "email": email,
            "meeting_notes": " ".join(notes_p),
            "products_discussed": prod_val,
            "request": req_str,
            "follow_up_date": fu_iso,
            "follow_up_display": fu_disp,
            "actions": actions,
            "evidence": evidence,
        }

        # Natural conversational Review Prompt
        if hcp_info.get("is_new") or (und and und.is_new_hcp):
            if is_te:
                conf_msg = f"{doc_name} ({hosp}) కొరకు కొత్త HCP ప్రొఫైల్ మరియు మీటింగ్ వివరాలు సిద్ధం చేశాను. ధృవీకరించి సేవ్ చేయమంటారా?"
            else:
                conf_msg = f"I've drafted a new HCP profile and meeting review for {doc_name} at {hosp}. Please review and confirm to save."
        else:
            fu_s = f" and follow-up on {fu_disp}" if fu_disp else ""
            p_s = f" discussing {prod_val}" if prod_val else ""
            if is_te:
                conf_msg = f"{doc_name} ({hosp}) తో మీటింగ్ వివరాలు సిద్ధం చేశాను. ధృవీకరించి సేవ్ చేయమంటారా?"
            else:
                conf_msg = f"Here is the meeting capture review for {doc_name} at {hosp}{p_s}{fu_s}. Please review and confirm to save."

        return {
            "pending_confirmation": True,
            "pending_action": pending_action,
            "response": conf_msg,
            "card_data": {
                "type": "meeting_capture_confirmation",
                "action_id": pending_action["action_id"],
                "doctor_name": doc_name,
                "hospital": hosp,
                "specialization": spec,
                "phone": phone or "Not specified",
                "email": email or "Not specified",
                "product": prod_val or "Not specified",
                "request": req_str or "Not specified",
                "follow_up": fu_disp or "Not scheduled",
                "actions": actions,
                "is_new_hcp": pending_action["is_new_hcp"],
                "evidence": pending_action.get("evidence"),
            },
            "current_hcp_id": hcp_info.get("id"),
            "current_hcp_name": doc_name,
            "current_hospital": hosp,
        }

    # Handle Single Follow-up Creation
    if intent in [INTENT_CREATE_FOLLOWUP, INTENT_CREATE_INTERACTION]:
        if not state.resolved_hcp:
            return {"needs_clarification": True, "clarification_type": "missing_entity", "response": "Follow-up schedule చేయడానికి ముందు ఏ doctor కోసమో చెప్పండి." if is_te else "Please specify which doctor you would like to schedule a follow-up with."}

        target_parsed = parse_date_expression(state.normalized_transcript or state.transcript)
        target_date = target_parsed[0] if target_parsed else datetime.now() + timedelta(days=7)
        date_str = target_parsed[1] if target_parsed else target_date.strftime("%B %d, %Y")

        pending_action = {
            "action_id": str(uuid.uuid4())[:8],
            "type": intent,
            "hcp_id": state.resolved_hcp["id"],
            "hcp_name": state.resolved_hcp["doctor_name"],
            "hospital": state.resolved_hcp["hospital"],
            "date": target_date.isoformat(),
            "date_display": date_str,
            "notes": state.transcript,
            "actions": ["CREATE_FOLLOWUP"],
        }

        doc_name = state.resolved_hcp["doctor_name"]
        hospital = state.resolved_hcp["hospital"]

        conf_msg = f"డాక్టర్ {doc_name} ({hospital}) తో {date_str} న follow-up schedule చేయమంటారా? Confirm చేయండి." if is_te else f"I found {doc_name} at {hospital}. You want to schedule a follow-up for {date_str}. Should I confirm and save this?"

        return {
            "pending_confirmation": True,
            "pending_action": pending_action,
            "response": conf_msg,
            "card_data": {
                "type": "confirmation_action",
                "action_id": pending_action["action_id"],
                "action": "CREATE_FOLLOWUP",
                "doctor_name": doc_name,
                "hospital": hospital,
                "date": date_str,
            },
        }

    return {}

def execute_crm_tool(state: VoiceCopilotState) -> dict:
    global _CURRENT_DB, EXECUTED_ACTION_IDS
    db = _CURRENT_DB
    intent = state.intent
    und = state.understanding
    hcp = state.resolved_hcp

    if intent == INTENT_CONFIRM_ACTION:
        if state.pending_action:
            action = state.pending_action
            act_type = action.get("type")
            act_id = action.get("action_id")

            # Duplicate protection
            if act_id and act_id in EXECUTED_ACTION_IDS:
                logger.info(f"[VoiceCopilot] Action {act_id} already executed. Skipping duplicate DB mutation.")
                c_data = {
                    "type": "meeting_schedule_card" if act_type == "SCHEDULE_MEETING" else "meeting_capture_card",
                    "status": "completed",
                    "is_completed": True,
                    "doctor_name": action.get("hcp_name"),
                    "hospital": action.get("hospital"),
                    "city": action.get("city"),
                    "location": action.get("location"),
                    "meeting_date_display": action.get("meeting_date_display"),
                    "meeting_time_display": action.get("meeting_time_display"),
                    "reminder_display": action.get("reminder_display"),
                }
                return {
                    "pending_confirmation": False,
                    "pending_action": None,
                    "card_data": c_data,
                    "tool_result": {
                        "type": "already_executed",
                        "doctor_name": action.get("hcp_name"),
                        "hospital": action.get("hospital"),
                        "city": action.get("city"),
                        "status": "completed",
                        "is_completed": True,
                        "duplicate_prevented": True,
                    }
                }

            # 1. Schedule Meeting Confirmation
            if act_type == "SCHEDULE_MEETING":
                try:
                    m_time_str = action.get("meeting_time")
                    try:
                        m_dt = datetime.fromisoformat(m_time_str) if m_time_str else datetime.now()
                    except Exception:
                        m_dt = datetime.now()

                    sched_res = schedule_meeting(
                        db=db,
                        user_id=state.user_id,
                        hcp_id=action.get("hcp_id", 1),
                        meeting_time=m_dt,
                        meeting_time_display=action.get("meeting_time_display"),
                        location=action.get("location"),
                        reminder_minutes=action.get("reminder_minutes", 30),
                    )

                    if act_id:
                        EXECUTED_ACTION_IDS.add(act_id)

                    card_data = {
                        "type": "meeting_schedule_card",
                        "doctor_name": action.get("hcp_name"),
                        "hospital": action.get("hospital"),
                        "city": action.get("city"),
                        "specialization": action.get("specialization"),
                        "location": action.get("location"),
                        "meeting_date_display": action.get("meeting_date_display"),
                        "meeting_time_display": action.get("meeting_time_display"),
                        "reminder_display": action.get("reminder_display"),
                        "status": "completed",
                        "is_completed": True,
                        "meeting": sched_res.get("meeting"),
                    }

                    return {
                        "pending_confirmation": False,
                        "pending_action": None,
                        "current_hcp_id": action.get("hcp_id"),
                        "current_hcp_name": action.get("hcp_name"),
                        "current_hospital": action.get("hospital"),
                        "card_data": card_data,
                        "tool_result": {
                            "type": "meeting_scheduled",
                            "success": sched_res.get("success", True),
                            "doctor_name": action.get("hcp_name"),
                            "hospital": action.get("hospital"),
                            "city": action.get("city"),
                            "specialization": action.get("specialization"),
                            "location": action.get("location"),
                            "meeting_date_display": action.get("meeting_date_display"),
                            "meeting_time_display": action.get("meeting_time_display"),
                            "reminder_display": action.get("reminder_display"),
                            "meeting": sched_res.get("meeting"),
                            "status": "completed",
                            "is_completed": True,
                        }
                    }
                except Exception as ex:
                    logger.error(f"[VoiceCopilot] Error scheduling meeting: {ex}")
                    if db:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                    return {
                        "pending_confirmation": True,
                        "tool_result": {"type": "error", "error": "I couldn't schedule that meeting due to a database issue. No CRM changes were committed."}
                    }

            # 2. Multi-Action: Create HCP + Interaction + Follow-up
            if action.get("is_new_hcp"):
                try:
                    # A. Create New Doctor
                    hcp_res = create_hcp(
                        db=db,
                        doctor_name=action.get("hcp_name", "Dr. New Doctor"),
                        hospital=action.get("hospital"),
                        specialization=action.get("specialization"),
                        city="Hyderabad",
                        phone=action.get("phone"),
                        email=action.get("email"),
                    )
                    created_hcp = hcp_res.get("hcp") or {}
                    created_hcp_id = created_hcp.get("id") or hcp_res.get("doctor_id")

                    # B. Create Interaction
                    int_res = create_interaction(
                        db=db,
                        user_id=state.user_id,
                        hcp_id=created_hcp_id,
                        notes=action.get("meeting_notes", "Meeting with new doctor logged via Voice Copilot"),
                        products_discussed=action.get("products_discussed", ""),
                        follow_up_date=datetime.fromisoformat(action["follow_up_date"]) if action.get("follow_up_date") else None,
                    )

                    if act_id:
                        EXECUTED_ACTION_IDS.add(act_id)

                    card_data = {
                        "type": "meeting_capture_card",
                        "doctor_name": action.get("hcp_name"),
                        "hospital": action.get("hospital"),
                        "city": action.get("city"),
                        "specialization": action.get("specialization"),
                        "follow_up_display": action.get("follow_up_display"),
                        "status": "completed",
                        "is_completed": True,
                        "is_new_hcp": True,
                    }

                    return {
                        "pending_confirmation": False,
                        "pending_action": None,
                        "current_hcp_id": created_hcp_id,
                        "current_hcp_name": action.get("hcp_name"),
                        "card_data": card_data,
                        "tool_result": {
                            "type": "new_hcp_created",
                            "success": True,
                            "doctor_name": action.get("hcp_name"),
                            "hospital": action.get("hospital"),
                            "city": action.get("city"),
                            "specialization": action.get("specialization"),
                            "follow_up_display": action.get("follow_up_display"),
                            "status": "completed",
                            "is_completed": True,
                        }
                    }
                except Exception as ex:
                    logger.error(f"[VoiceCopilot] Error creating new HCP and meeting: {ex}")
                    if db:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                    return {
                        "pending_confirmation": True,
                        "tool_result": {"type": "error", "error": f"Failed to create new doctor: {str(ex)}"}
                    }

            # 3. Existing HCP Meeting Capture
            if act_type == INTENT_CAPTURE_MEETING:
                fu_date = datetime.fromisoformat(action["follow_up_date"]) if action.get("follow_up_date") and "CREATE_FOLLOWUP" in action.get("actions", []) else None
                try:
                    write_res = create_interaction(
                        db=db,
                        user_id=state.user_id,
                        hcp_id=action["hcp_id"],
                        notes=action.get("meeting_notes", "Meeting logged via Voice Copilot"),
                        products_discussed=action.get("products_discussed", ""),
                        follow_up_date=fu_date,
                    )
                    if act_id:
                        EXECUTED_ACTION_IDS.add(act_id)

                    return {
                        "pending_confirmation": False,
                        "pending_action": None,
                        "tool_result": {
                            "type": "meeting_captured",
                            "success": write_res.get("success", True),
                            "doctor_name": action.get("hcp_name"),
                            "follow_up_display": action.get("follow_up_display") if "CREATE_FOLLOWUP" in action.get("actions", []) else None,
                            "interaction_id": write_res.get("interaction", {}).get("id"),
                        }
                    }
                except Exception as ex:
                    logger.error(f"[VoiceCopilot] Error saving meeting: {ex}")
                    if db:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                    return {
                        "pending_confirmation": True,
                        "tool_result": {"type": "error", "error": f"Failed to save meeting: {str(ex)}"}
                    }

            # 4. Single Follow-up
            target_date = datetime.fromisoformat(action["date"]) if action.get("date") else None
            try:
                write_res = create_interaction(
                    db=db,
                    user_id=state.user_id,
                    hcp_id=action["hcp_id"],
                    notes=action.get("notes", "Follow-up created via Voice Copilot"),
                    products_discussed="",
                    follow_up_date=target_date,
                )
                if act_id:
                    EXECUTED_ACTION_IDS.add(act_id)

                return {
                    "pending_confirmation": False,
                    "pending_action": None,
                    "tool_result": {
                        "type": "action_confirmed",
                        "success": write_res.get("success", True),
                        "doctor_name": action.get("hcp_name"),
                        "date": action.get("date_display"),
                    }
                }
            except Exception as ex:
                logger.error(f"[VoiceCopilot] Error creating follow-up: {ex}")
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                return {
                    "pending_confirmation": True,
                    "tool_result": {"type": "error", "error": f"Failed to create follow-up: {str(ex)}"}
                }

    if intent == INTENT_CANCEL_ACTION:
        return {
            "pending_confirmation": False,
            "pending_action": None,
            "tool_result": {"type": "action_cancelled"}
        }

    if state.pending_confirmation or state.needs_clarification:
        return {}

    # Read Tools
    # Advanced CRM Intelligence Tools
    if intent == INTENT_GET_NEXT_ACTION:
        next_act = get_next_action(db, user_id=state.user_id)
        return {"tool_result": {"type": "next_action", "next_action": next_act}}
    if intent == INTENT_GET_CRM_BRIEF:
        brief = get_crm_day_brief(db, user_id=state.user_id)
        return {"tool_result": {"type": "crm_day_brief", "brief": brief}}

    if intent == INTENT_GET_PRE_MEETING_INTELLIGENCE:
        target_hcp = hcp
        if not target_hcp and state.entity_name:
            matches = search_hcps(db, state.entity_name)
            if matches:
                target_hcp = matches[0]
        if target_hcp:
            intel = get_pre_meeting_intelligence(db, target_hcp["id"])
            return {"tool_result": {"type": "pre_meeting_intelligence", "hcp": target_hcp, "intelligence": intel}, "current_hcp_id": target_hcp["id"], "current_hcp_name": target_hcp["doctor_name"]}
        return {"tool_result": {"type": "not_found", "query": state.entity_name or state.transcript}}

    if intent == INTENT_GET_CRM_ANALYTICS:
        metric = (und.analytics_metric if und and und.analytics_metric else "weekly_meetings")
        analytics = get_crm_analytics(db, user_id=state.user_id, metric=metric)
        return {"tool_result": {"type": "crm_analytics", "metric": metric, "analytics": analytics}}

    if intent in [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP]:
        if hcp:
            return {"tool_result": {"type": "hcp_details", "hcp": hcp}}
        # Search across all HCPs
        q = state.entity_name or state.normalized_transcript or state.transcript
        matches = search_hcps(db, q)
        if matches:
            return {"tool_result": {"type": "hcp_details", "hcp": matches[0]}}
        return {"tool_result": {"type": "not_found", "query": q}}

    if intent == INTENT_GET_HCP_INTERACTIONS:
        if hcp:
            interactions = get_hcp_interactions(db, hcp["id"], limit=3)
            return {"tool_result": {"type": "hcp_interactions", "hcp": hcp, "interactions": interactions}}
        return {"tool_result": {"type": "not_found", "query": state.entity_name or state.transcript}}

    if intent == INTENT_GET_HCP_FOLLOWUPS:
        if hcp:
            followups = get_hcp_followups(db, hcp["id"])
            return {"tool_result": {"type": "hcp_followups", "hcp": hcp, "followups": followups}}
        return {"tool_result": {"type": "not_found", "query": state.entity_name or state.transcript}}

    if intent == INTENT_GET_ALL_FOLLOWUPS:
        t_filter = und.time_filter if und else "all"
        all_fu = get_all_followups(db, user_id=state.user_id, limit=10, time_filter=t_filter)
        return {"tool_result": {"type": "all_followups", "followups": all_fu, "time_filter": t_filter}}

    if intent == INTENT_GET_RECENT_INTERACTIONS:
        recent = get_recent_interactions(db, user_id=state.user_id, limit=5)
        return {"tool_result": {"type": "recent_interactions", "interactions": recent}}

    if intent == INTENT_GET_PRODUCT_DISCUSSIONS:
        prod_name = state.entity_product or (und.product if und else None) or "CardioPress-50"
        discussions = get_product_discussions(db, prod_name, user_id=state.user_id)
        return {"tool_result": {"type": "product_discussions", "product": prod_name, "discussions": discussions}}

    if intent == INTENT_GET_HOSPITAL_DETAILS:
        h_name = state.entity_hospital or (und.hospital if und else None) or "Apollo Hospital"
        doctors = get_hospital_doctors(db, h_name)
        return {"tool_result": {"type": "hospital_doctors", "hospital": h_name, "doctors": doctors}}

    search_res = search_interactions(db, state.normalized_transcript or state.transcript, user_id=state.user_id)
    return {"tool_result": {"type": "search_interactions", "results": search_res}}


def validate_and_format(state: VoiceCopilotState) -> dict:
    if state.card_data:
        return {"card_data": state.card_data}

    tool_res = state.tool_result or {}
    res_type = tool_res.get("type", "")

    if state.needs_clarification and state.clarification_type == "ambiguity":
        return {"card_data": {"type": "ambiguity_card", "candidates": state.ambiguous_candidates}}

    if res_type == "next_action":
        return {"card_data": {"type": "next_action_card", "next_action": tool_res.get("next_action", {})}}

    if res_type == "meeting_scheduled":
        return {
            "card_data": {
                "type": "meeting_schedule_card",
                "meeting": tool_res.get("meeting", {}),
                "doctor_name": tool_res.get("doctor_name"),
                "hospital": tool_res.get("hospital"),
                "meeting_date_display": tool_res.get("meeting_date_display"),
                "meeting_time_display": tool_res.get("meeting_time_display"),
                "reminder_display": tool_res.get("reminder_display"),
            }
        }

    if res_type == "crm_day_brief":
        return {"card_data": {"type": "crm_brief_card", "brief": tool_res.get("brief", {})}}

    if res_type == "pre_meeting_intelligence":
        return {"card_data": {"type": "pre_meeting_intelligence_card", "hcp": tool_res.get("hcp", {}), "intelligence": tool_res.get("intelligence", {})}}

    if res_type == "crm_analytics":
        return {"card_data": {"type": "analytics_card", "metric": tool_res.get("metric"), "analytics": tool_res.get("analytics", {})}}

    if res_type == "hcp_details":
        hcp = tool_res.get("hcp", {})
        return {
            "card_data": {
                "type": "hcp_card",
                "doctor_name": hcp.get("doctor_name"),
                "specialization": hcp.get("specialization"),
                "hospital": hcp.get("hospital"),
                "city": hcp.get("city"),
                "phone": hcp.get("phone"),
                "email": hcp.get("email"),
            }
        }

    if res_type == "hospital_details":
        return {
            "card_data": {
                "type": "hospital_card",
                "hospital_name": tool_res.get("hospital_name"),
                "doctors": tool_res.get("doctors", []),
            }
        }

    if res_type == "recent_interactions":
        return {
            "card_data": {
                "type": "recent_interactions_card",
                "interactions": tool_res.get("interactions", []),
            }
        }

    if res_type == "product_discussions":
        return {
            "card_data": {
                "type": "product_discussions_card",
                "product_name": tool_res.get("product_name"),
                "interactions": tool_res.get("interactions", []),
            }
        }

    if res_type == "hcp_interactions":
        return {
            "card_data": {
                "type": "interaction_card",
                "doctor_name": tool_res.get("doctor_name"),
                "interactions": tool_res.get("interactions", []),
            }
        }

    if res_type == "hcp_followups":
        return {
            "card_data": {
                "type": "followups_list_card",
                "doctor_name": tool_res.get("doctor_name"),
                "followups": tool_res.get("followups", []),
            }
        }

    return {"card_data": None}


def generate_response(state: VoiceCopilotState) -> dict:
    if state.response:
        return {"response": state.response}

    tool_res = state.tool_result or {}
    res_type = tool_res.get("type", "")
    is_te = state.language in ["te", "mixed"]

    if state.needs_clarification and state.clarification_type == "ambiguity":
        candidates = state.ambiguous_candidates
        names = ", ".join([f"{c['doctor_name']} ({c['hospital']})" for c in candidates[:2]])
        resp = f"నాకు ఈ పేరుతో పలువురు డాక్టర్లు కనిపించారు: {names}. మీరు ఏ డాక్టర్ గురించి అడుగుతున్నారు?" if is_te else f"I found multiple HCPs matching that name: {names}. Which one did you mean?"
        return {"response": resp}

    if res_type == "error":
        return {"response": tool_res.get("error", "An error occurred while performing the CRM operation.")}

    if res_type == "meeting_scheduled":
        doc = tool_res.get("doctor_name", "Doctor")
        dt_disp = tool_res.get("meeting_date_display", "scheduled date")
        tm_disp = tool_res.get("meeting_time_display", "3:00 PM")
        rem = tool_res.get("reminder_display")
        rem_str = f" ({rem} reminder సెట్ చేశాను)" if is_te and rem else (f" with a {rem} reminder" if rem else "")
        if is_te:
            resp = f"సరే. డాక్టర్ {doc} తో {dt_disp} {tm_disp} కి మీటింగ్ షెడ్యూల్ చేశాను{rem_str}."
        else:
            resp = f"Done. I have scheduled the meeting with {doc} for {dt_disp} at {tm_disp}{rem_str}."
        return {"response": resp}

    if res_type == "next_action":
        na = tool_res.get("next_action", {})
        head = na.get("headline", "")
        exp = na.get("explanation", "Review your upcoming CRM priorities.")
        full_text = f"{head} {exp}".strip() if head and head not in exp else exp
        if is_te:
            return {"response": f"మీ తదుపరి ముఖ్యమైన చర్య: {full_text}"}
        return {"response": full_text}

    if res_type == "new_hcp_created":
        doc = tool_res.get("doctor_name", "the doctor")
        fu = tool_res.get("follow_up_display")
        if fu:
            resp = f"సరే. డాక్టర్ {doc}ని CRM లో create చేశాను మరియు {fu} follow-up schedule చేశాను." if is_te else f"Done. I created {doc} in your HCP directory and scheduled the {fu} follow-up."
        else:
            resp = f"సరే. డాక్టర్ {doc}ని HCP డైరెక్టరీలో create చేసి meeting log చేశాను." if is_te else f"Done. I created {doc} in your HCP directory and logged the meeting."
        return {"response": resp}

    if res_type == "meeting_captured":
        doc = tool_res.get("doctor_name", "the doctor")
        fu_disp = tool_res.get("follow_up_display")
        if fu_disp:
            resp = f"సరే. డాక్టర్ {doc}తో interaction log చేశాను మరియు {fu_disp} follow-up create చేశాను." if is_te else f"Done. I logged the interaction with {doc} and created the {fu_disp} follow-up."
        else:
            resp = f"సరే. డాక్టర్ {doc}తో interaction log చేశాను." if is_te else f"Done. I logged the interaction with {doc}."
        return {"response": resp}

    if res_type == "action_confirmed":
        doc = tool_res.get("doctor_name", "doctor")
        dt = tool_res.get("date", "scheduled date")
        resp = f"డాక్టర్ {doc} తో {dt} న follow-up విజయవంతంగా schedule చేయబడింది." if is_te else f"Follow-up with {doc} has been successfully scheduled for {dt}."
        return {"response": resp}

    if res_type == "action_cancelled":
        resp = "Meeting log చేయడం మరియు follow-up రద్దు చేశాను." if is_te else "Meeting logging and follow-up have been cancelled."
        return {"response": resp}

    if res_type == "already_executed":
        return {"response": "This action was already confirmed and saved. No duplicate changes were made."}

    if res_type == "crm_day_brief":
        b = tool_res.get("brief", {})
        try:
            c_fu = int(b.get("today_followups_count") or 0)
        except Exception:
            c_fu = 0
        try:
            c_doc = int(b.get("doctors_to_visit_count") or 0)
        except Exception:
            c_doc = 0
        try:
            c_od = int(b.get("overdue_followups_count") or 0)
        except Exception:
            c_od = 0
        try:
            c_mt = int(b.get("today_meetings_count") or 0)
        except Exception:
            c_mt = 0

        if c_mt == 0 and c_fu == 0 and c_od == 0:
            if is_te:
                resp = "ఈరోజు మీకు షెడ్యూల్ చేసిన మీటింగ్‌లు, ఫాలో-అప్‌లు లేదా ఓవర్‌డ్యూ టాస్క్‌లు ఏమీ లేవు. మీ షెడ్యూల్ క్లియర్‌గా ఉంది."
            else:
                resp = "You're clear today. You have no meetings, follow-ups, or overdue tasks."
        else:
            if is_te:
                resp = f"ఈరోజు మీ CRM బ్రీఫింగ్: {c_mt} meetings, {c_fu} follow-ups ({c_doc} doctors), {c_od} overdue follow-ups ఉన్నాయి."
            else:
                resp = f"Here is your CRM briefing for today: {c_mt} meeting(s), {c_fu} follow-up(s) across {c_doc} doctor(s), and {c_od} overdue follow-up(s)."
        return {"response": resp}

    if res_type == "pre_meeting_intelligence":
        intel = tool_res.get("intelligence", {})
        doc = tool_res.get("hcp", {}).get("doctor_name", "Doctor")
        hosp = tool_res.get("hcp", {}).get("hospital", "")
        prods = ", ".join(intel.get("products_discussed_history", [])) or "General discussion"
        if is_te:
            resp = f"{doc} ({hosp}) తో మీటింగ్ బ్రీఫింగ్: మునుపు {prods} గురించి చర్చించారు. వివరాలు కార్డ్‌లో చూడండి."
        else:
            resp = f"Pre-meeting briefing for {doc} at {hosp}: Previously discussed products include {prods}. Review past commitments and recent notes above."
        return {"response": resp}

    if res_type == "crm_analytics":
        a = tool_res.get("analytics", {})
        title = a.get("title", "CRM Analytics")
        total = a.get("total_count", 0)
        period = a.get("period", "")
        if is_te:
            resp = f"{title} ({period}): మొత్తం {total} రికార్డులు కనుగొనబడ్డాయి."
        else:
            resp = f"{title} ({period}): {total} record(s) found in your CRM."
        return {"response": resp}

    if res_type == "hcp_details":
        hcp = tool_res.get("hcp", {})
        doc = hcp.get("doctor_name", "")
        hosp = hcp.get("hospital", "")
        city = hcp.get("city", "")
        spec = hcp.get("specialization", "")
        resp = f"{doc} {hosp} ({city}) లో {spec} గా పని చేస్తున్నారు." if is_te else f"{doc} works at {hosp} in {city} as a {spec}."
        return {"response": resp}

    if res_type == "hcp_interactions":
        hcp = tool_res.get("hcp", {})
        doc = hcp.get("doctor_name", "")
        interactions = tool_res.get("interactions", [])
        if not interactions:
            return {"response": f"{doc} తో ఇంకా ఏ meetings రికార్డ్ కాలేదు." if is_te else f"No meetings recorded with {doc} yet."}
        last_i = interactions[0]
        dt = (last_i.get("created_at") or "")[:10]
        prod = last_i.get("products_discussed") or ""
        prod_str = f" {prod} గురించి చర్చించారు." if prod else "."
        resp = f"మీరు {doc} ని చివరిసారి {dt} న కలిశారు.{prod_str}" if is_te else f"You last met {doc} on {dt}. Products discussed: {prod or 'General relationship'}."
        return {"response": resp}

    if res_type == "hcp_followups":
        hcp = tool_res.get("hcp", {})
        doc = hcp.get("doctor_name", "")
        followups = tool_res.get("followups", [])
        if not followups:
            return {"response": f"{doc} తో upcoming follow-ups ఏమీ schedule కాలేదు." if is_te else f"No upcoming follow-ups scheduled for {doc}."}
        next_f = followups[0]
        dt = (next_f.get("follow_up_date") or "")[:10]
        resp = f"{doc} తో next follow-up {dt} న schedule అయింది." if is_te else f"Next follow-up with {doc} is scheduled for {dt}."
        return {"response": resp}

    if res_type == "all_followups":
        followups = tool_res.get("followups", [])
        tf = tool_res.get("time_filter", "all")
        if not followups:
            if tf == "today":
                return {"response": "ఈరోజు మీకు scheduled follow-ups ఏమీ లేవు." if is_te else "You have no follow-ups scheduled for today."}
            return {"response": "మీకు scheduled follow-ups ఏమీ లేవు." if is_te else "You have no upcoming follow-ups scheduled."}
        summary_items = [f"{f.get('hcp_name') or 'Doctor'} ({(f.get('follow_up_date') or '')[:10]})" for f in followups[:3]]
        joined = ", ".join(summary_items)
        resp = f"మీకు {len(followups)} follow-ups schedule అయి ఉన్నాయి: {joined}." if is_te else f"You have {len(followups)} upcoming follow-ups: {joined}."
        return {"response": resp}

    if res_type == "product_discussions":
        prod = tool_res.get("product", "product")
        discussions = tool_res.get("discussions", [])
        if not discussions:
            return {"response": f"{prod} గురించి ఇంకా ఎవరితోనూ మాట్లాడలేదు." if is_te else f"No recorded discussions found for {prod}."}
        docs = ", ".join([d.get("hcp_name") or "Doctor" for d in discussions[:3]])
        resp = f"{prod} గురించి మీరు {docs} తో మాట్లాడారు." if is_te else f"You discussed {prod} with {docs}."
        return {"response": resp}

    if res_type == "hospital_doctors":
        hosp = tool_res.get("hospital", "hospital")
        doctors = tool_res.get("doctors", [])
        if not doctors:
            return {"response": f"{hosp} లో ఏ డాక్టర్లూ రిజిస్టర్ కాలేదు." if is_te else f"No doctors found at {hosp}."}
        doc_names = ", ".join([d.get("doctor_name", "") for d in doctors[:4]])
        resp = f"{hosp} లో ఉన్న డాక్టర్లు: {doc_names}." if is_te else f"Doctors at {hosp}: {doc_names}."
        return {"response": resp}

    if res_type == "recent_interactions":
        interactions = tool_res.get("interactions", [])
        if not interactions:
            return {"response": "మీకు recent meetings ఏమీ లేవు." if is_te else "No recent interactions found."}
        last_i = interactions[0]
        doc = last_i.get("hcp_name") or "Doctor"
        dt = (last_i.get("created_at") or "")[:10]
        resp = f"మీరు ఇటీవల {dt} న {doc} ని కలిశారు." if is_te else f"Your most recent meeting was with {doc} on {dt}."
        return {"response": resp}

    if res_type == "not_found":
        q = tool_res.get("query", "")
        resp = f"'{q}' గురించి CRM లో సమాచారం దొరకలేదు." if is_te else f"I couldn't find CRM records matching '{q}'."
        return {"response": resp}

    return {"response": "ఈ ప్రశ్నకు సంబంధించిన CRM సమాచారం దొరకలేదు." if is_te else "I couldn't find relevant information in the CRM."}


workflow = StateGraph(VoiceCopilotState)

workflow.add_node("normalize_input", normalize_input)
workflow.add_node("llm_understand", llm_understand)
workflow.add_node("resolve_entities", resolve_entities)
workflow.add_node("plan_actions_and_review", plan_actions_and_review)
workflow.add_node("execute_crm_tool", execute_crm_tool)
workflow.add_node("validate_and_format", validate_and_format)
workflow.add_node("generate_response", generate_response)

workflow.add_edge(START, "normalize_input")
workflow.add_edge("normalize_input", "llm_understand")
workflow.add_edge("llm_understand", "resolve_entities")
workflow.add_edge("resolve_entities", "plan_actions_and_review")
workflow.add_edge("plan_actions_and_review", "execute_crm_tool")
workflow.add_edge("execute_crm_tool", "validate_and_format")
workflow.add_edge("validate_and_format", "generate_response")
workflow.add_edge("generate_response", END)

compiled_copilot_graph = workflow.compile()


def run_voice_copilot_graph(
    db,
    transcript: str,
    user_id: int,
    history: Optional[List[Dict[str, str]]] = None,
    current_hcp_id: Optional[int] = None,
    current_hcp_name: Optional[str] = None,
    pending_confirmation: bool = False,
    pending_action: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    global _CURRENT_DB
    _CURRENT_DB = db

    initial_state = VoiceCopilotState(
        user_id=user_id,
        transcript=transcript,
        history=history or [],
        current_hcp_id=current_hcp_id,
        current_hcp_name=current_hcp_name,
        pending_confirmation=pending_confirmation,
        pending_action=pending_action,
    )

    try:
        invoked = compiled_copilot_graph.invoke(initial_state)

        if isinstance(invoked, dict):
            final = invoked
        elif hasattr(invoked, "model_dump"):
            final = invoked.model_dump()
        elif hasattr(invoked, "__dict__"):
            final = invoked.__dict__
        else:
            final = {}

        return {
            "success": True,
            "response": final.get("response", ""),
            "language": final.get("language", "en"),
            "intent": final.get("intent", INTENT_UNKNOWN),
            "hcp_id": final.get("current_hcp_id"),
            "hcp_name": final.get("current_hcp_name"),
            "current_hcp_id": final.get("current_hcp_id"),
            "current_hcp_name": final.get("current_hcp_name"),
            "current_hospital": final.get("current_hospital"),
            "pending_confirmation": final.get("pending_confirmation", False),
            "pending_action": final.get("pending_action"),
            "needs_clarification": final.get("needs_clarification", False),
            "clarification_type": final.get("clarification_type"),
            "ambiguous_candidates": final.get("ambiguous_candidates", []),
            "card_data": final.get("card_data"),
            "confidence": final.get("confidence", 1.0),
            "conversation_id": conversation_id,
        }
    except Exception as e:
        logger.error(f"[VoiceCopilot] Execution error: {e}", exc_info=True)
        return {
            "success": False,
            "response": "I encountered an error while querying the CRM.",
            "language": "en",
            "intent": INTENT_UNKNOWN,
            "hcp_id": None,
            "hcp_name": None,
            "current_hcp_id": None,
            "current_hcp_name": None,
            "current_hospital": None,
            "pending_confirmation": False,
            "pending_action": None,
            "needs_clarification": False,
            "clarification_type": None,
            "ambiguous_candidates": [],
            "card_data": None,
            "error": "I encountered an error while querying the CRM.",
            "conversation_id": conversation_id,
        }
