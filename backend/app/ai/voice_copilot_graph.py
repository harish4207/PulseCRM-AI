"""
Voice Copilot Graph: True Conversational CRM Agent Architecture
==============================================================
Implements the multi-turn stateful pipeline:
User Conversation -> Semantic Understanding -> Entity Resolution -> Evolving CRM Record
-> Action Planning & Review -> Human Confirmation -> Atomic CRM Transaction -> Verification -> Grounded Response
"""

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
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.meeting_reminder import MeetingReminder

from app.ai.normalizer import normalize_transcript, extract_clean_search_tokens, clean_doctor_name, is_valid_person_name
from app.ai.fuzzy_matcher import (
    normalize_text,
    match_hcp_from_db,
    match_hospital_from_db,
    match_product_from_transcript,
    calculate_similarity,
)
from app.ai.conversation_models import (
    HcpDraft,
    InteractionDraft,
    FollowUpDraft,
    MeetingDraft,
    EvolvingCrmRecord,
    ConversationState,
)
from app.ai.meeting_extractor import (
    parse_date_expression,
    extract_request_action,
    apply_meeting_correction,
    apply_meeting_schedule_correction,
    extract_meeting_schedule_details,
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
    execute_atomic_crm_transaction,
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
    preferred_provider: Optional[str] = None


_CURRENT_DB = None


def normalize_input(state: VoiceCopilotState) -> dict:
    raw = (state.transcript or "").strip()
    norm = normalize_transcript(raw)
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
        preferred_provider=state.preferred_provider,
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
    """
    Entity Resolution Strategy (Strict Priority):
    1. Explicit doctor in current message / correction target (overrides ALL past context)
    2. Anaphoric reference (him, her, aayana) -> uses active context
    3. Fuzzy / Phonetic CRM database match
    4. Explicit new HCP creation request
    """
    global _CURRENT_DB
    db = _CURRENT_DB
    und = state.understanding

    # Priority 1: Explicit Override / Negation (e.g. "Rajesh kaadu Sharma doctor", "Not Rajesh, I meant Sharma")
    if (state.is_override and state.override_target) or (und and und.is_override and und.override_target):
        raw_target = state.override_target or (und.override_target if und else None)
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

    # Skip DB resolution for confirmation/cancellation/CRM analytics/briefing
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

    # Priority 2: Explicit doctor mentioned in current turn (ALWAYS overrides stale context to avoid contamination)
    explicit_doctor = und.doctor_name if und and und.doctor_name else state.entity_name
    if explicit_doctor and not (state.is_anaphoric or (und and und.is_anaphoric)):
        clean_name = clean_doctor_name(explicit_doctor) or explicit_doctor
        match_result = match_hcp_from_db(db, clean_name)
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

        if state.intent in [INTENT_CAPTURE_MEETING, INTENT_CREATE_INTERACTION, INTENT_CREATE_HCP] or (und and und.is_new_hcp):
            # If not in DB, create new doctor entity proposal cleanly without old context contamination
            return {
                "resolved_hcp": {
                    "id": None,
                    "doctor_name": clean_name,
                    "hospital": und.hospital or "Hospital",
                    "specialization": und.specialization or "Cardiologist",
                    "phone": und.phone,
                    "email": und.email,
                    "is_new": True,
                },
                "current_hcp_id": None,
                "current_hcp_name": clean_name,
                "current_hospital": und.hospital,
                "confidence": 0.95,
                "needs_clarification": False,
            }

        return {
            "resolved_hcp": None,
            "current_hcp_id": None,
            "current_hcp_name": clean_name,
            "current_hospital": und.hospital,
            "confidence": 0.4,
            "needs_clarification": False,
        }

    # Priority 3: Anaphoric reference (e.g. "When did I last meet him?", "Aayana last meeting eppudu?")
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

    # Priority 4: Search DB by transcript tokens (only for inquiry / lookup intents or when doctor candidate token exists)
    if state.intent not in [INTENT_CAPTURE_MEETING, INTENT_SCHEDULE_MEETING] or (und and und.doctor_name):
        query_text = state.normalized_transcript or state.transcript
        match_result = match_hcp_from_db(db, query_text)
        best_match = match_result.get("best_match")
        if best_match and match_result.get("confidence", 0.0) >= 0.65:
            return {
                "resolved_hcp": best_match,
                "current_hcp_id": best_match["id"],
                "current_hcp_name": best_match["doctor_name"],
                "current_hospital": best_match.get("hospital"),
                "confidence": match_result.get("confidence", 0.0),
                "needs_clarification": False,
            }

    return {"resolved_hcp": None, "confidence": 0.4, "needs_clarification": False}


def plan_actions_and_review(state: VoiceCopilotState) -> dict:
    global _CURRENT_DB
    db = _CURRENT_DB
    intent = state.intent
    und = state.understanding
    is_te = state.language in ["te", "mixed"]

    if state.needs_clarification and state.clarification_type == "ambiguity":
        return {}

    # 0. Handle Progressive In-Progress Draft Evolution (New Doctor multi-turn accumulation)
    if state.pending_action and not state.pending_confirmation:
        act = dict(state.pending_action)
        is_draft_updated = False
        update_desc = []

        if und and und.doctor_name and is_valid_person_name(und.doctor_name):
            d_clean = clean_doctor_name(und.doctor_name)
            act["hcp_name"] = d_clean
            act["doctor_name"] = d_clean
            act["is_new_hcp"] = True
            is_draft_updated = True
            update_desc.append(f"Doctor: {d_clean}")

        if und and und.hospital:
            act["hospital"] = und.hospital
            is_draft_updated = True
            update_desc.append(f"Hospital: {und.hospital}")

        if und and und.specialization:
            act["specialization"] = und.specialization
            is_draft_updated = True
            update_desc.append(f"Specialization: {und.specialization}")

        if und and und.city:
            act["city"] = und.city
            is_draft_updated = True
            update_desc.append(f"City: {und.city}")

        if und and und.phone:
            act["phone"] = und.phone
            is_draft_updated = True
            update_desc.append(f"Phone: {und.phone}")

        if und and und.email:
            act["email"] = und.email
            is_draft_updated = True
            update_desc.append(f"Email: {und.email}")

        if und and und.product:
            act["products_discussed"] = und.product
            act["product"] = und.product
            is_draft_updated = True
            update_desc.append(f"Product: {und.product}")

        if und and und.doctor_request:
            act["doctor_request"] = und.doctor_request
            act["request"] = und.doctor_request
            is_draft_updated = True
            update_desc.append(f"Request: {und.doctor_request}")

        if und and und.follow_up_display and not und.meeting_time_display and intent != INTENT_SCHEDULE_MEETING:
            act["follow_up_display"] = und.follow_up_display
            act["follow_up_date"] = und.follow_up_date
            if "CREATE_FOLLOWUP" not in act.get("actions", []):
                act["actions"] = list(act.get("actions", [])) + ["CREATE_FOLLOWUP"]
            is_draft_updated = True
            update_desc.append(f"Follow-up: {und.follow_up_display}")

        if und and (und.meeting_time_display or intent == INTENT_SCHEDULE_MEETING):
            act["type"] = "SCHEDULE_MEETING"
            if und.meeting_time_display:
                act["meeting_time_display"] = und.meeting_time_display
            if und.follow_up_display:
                act["meeting_date_display"] = und.follow_up_display
            if "CREATE_MEETING" not in act.get("actions", []):
                act["actions"] = list(act.get("actions", [])) + ["CREATE_MEETING"]
            is_draft_updated = True

        if und and und.reminder_display:
            if und.reminder_minutes == 0 or und.reminder_display == "No reminder":
                act["reminder_display"] = "No reminder"
                act["reminder_minutes"] = 0
                act["actions"] = [a for a in act.get("actions", []) if a != "CREATE_REMINDER"]
            else:
                act["reminder_display"] = und.reminder_display
                act["reminder_minutes"] = und.reminder_minutes or 30
                if "CREATE_REMINDER" not in act.get("actions", []):
                    act["actions"] = list(act.get("actions", [])) + ["CREATE_REMINDER"]
            is_draft_updated = True

        if "keep everything" in state.transcript.lower():
            is_draft_updated = True

        if is_draft_updated:
            doc_n = act.get("hcp_name") or act.get("doctor_name")
            hosp = act.get("hospital")
            spec = act.get("specialization")
            city = act.get("city")
            ph = act.get("phone")
            prod = act.get("products_discussed") or act.get("product")
            req = act.get("doctor_request") or act.get("request")

            # Check if this draft is ready for a meeting schedule review or capture review
            if doc_n and (act.get("type") == "SCHEDULE_MEETING" or intent == INTENT_SCHEDULE_MEETING or "CREATE_MEETING" in act.get("actions", [])):
                dt_disp = act.get("meeting_date_display") or "Friday"
                tm_disp = act.get("meeting_time_display") or "03:00 PM"
                rem_disp = act.get("reminder_display") or "30 minutes before"
                rem_s_en = f" (with a {rem_disp} reminder)" if rem_disp and rem_disp.lower() not in ["none", "no reminder"] else ""
                rem_s_te = f" ({rem_disp} reminder తో)" if rem_disp and rem_disp.lower() not in ["none", "no reminder"] else ""

                card_data = {
                    "type": "meeting_schedule_confirmation",
                    "action_id": act.get("action_id") or str(uuid.uuid4())[:8],
                    "doctor_name": doc_n,
                    "hospital": hosp or "Hospital",
                    "city": city or "",
                    "specialization": spec or "",
                    "meeting_date_display": dt_disp,
                    "meeting_time_display": tm_disp,
                    "location": f"{hosp} · {city}" if hosp and city else (hosp or "Hospital"),
                    "reminder_display": rem_disp,
                    "actions": act.get("actions", ["CREATE_MEETING"]),
                }
                prompt = (
                    f"{doc_n} ({hosp or 'Hospital'}) తో {dt_disp} న {tm_disp} కి meeting రివ్యూ సిద్ధంగా ఉంది{rem_s_te}. షెడ్యూల్ చేయడానికి confirm చేయండి."
                    if is_te
                    else f"Here is the meeting review for {doc_n} at {hosp or 'Hospital'} on {dt_disp} at {tm_disp}{rem_s_en}. Please review and confirm to schedule."
                )
                return {
                    "pending_confirmation": True,
                    "pending_action": act,
                    "current_hcp_id": None,
                    "current_hcp_name": doc_n,
                    "current_hospital": hosp,
                    "card_data": card_data,
                    "response": prompt,
                }

            # If doctor name was just provided
            if und.doctor_name and is_valid_person_name(und.doctor_name) and not hosp and not spec:
                prompt = f"I've noted {doc_n}. What hospital or clinic are they affiliated with?"
                return {
                    "pending_confirmation": False,
                    "pending_action": act,
                    "current_hcp_name": doc_n,
                    "response": prompt,
                }

            # If hospital or specialization was just provided
            if (und.hospital or und.specialization) and not ph and not prod:
                loc_desc = f" at {hosp}" if hosp else ""
                spec_desc = f" is a {spec}" if spec else ""
                prompt = f"Got it. {doc_n}{spec_desc}{loc_desc}."
                return {
                    "pending_confirmation": False,
                    "pending_action": act,
                    "current_hcp_name": doc_n,
                    "current_hospital": hosp,
                    "response": prompt,
                }

            # If phone was just provided
            if und.phone and not prod:
                prompt = f"Updated phone number for {doc_n} to {ph}."
                return {
                    "pending_confirmation": False,
                    "pending_action": act,
                    "current_hcp_name": doc_n,
                    "response": prompt,
                }

            # If product or request was just provided
            if prod or req:
                p_text = f"discussion on {prod}" if prod else ""
                r_text = f"request for {req}" if req else ""
                joined = " and ".join([t for t in [p_text, r_text] if t])
                prompt = f"Noted {joined} with {doc_n}."
                return {
                    "pending_confirmation": False,
                    "pending_action": act,
                    "current_hcp_name": doc_n,
                    "response": prompt,
                }

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

        if not target_hcp or not target_hcp.get("id"):
            cand_name = clean_doctor_name((und.doctor_name if und else None) or state.entity_name or state.current_hcp_name or "the doctor")
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

        if conflict_info.get("is_conflict"):
            conf_doc = conflict_info.get("conflicting_meeting", {}).get("doctor_name", "another doctor")
            conf_time = conflict_info.get("conflicting_meeting", {}).get("meeting_time_display", "the same time")
            prompt = (
                f"మీకు ఇప్పటికే {conf_time} కి {conf_doc} తో meeting ఉంది. {doc_name} తో {dt_disp} {tm_disp} కి meeting షెడ్యూల్ చేయమంటారా?"
                if is_te
                else f"Possible conflict: You already have a meeting with {conf_doc} at {conf_time}. Would you like me to schedule the meeting with {doc_name} on {dt_disp} at {tm_disp} anyway?"
            )
        else:
            prompt = (
                f"{doc_name} ({hosp}) తో {dt_disp} న {tm_disp} కి meeting రివ్యూ సిద్ధంగా ఉంది{rem_s_te}. షెడ్యూల్ చేయడానికి confirm చేయండి."
                if is_te
                else f"Here is the meeting review for {doc_name} at {hosp} on {dt_disp} at {tm_disp}{rem_s_en}. Please review and confirm to schedule."
            )

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
            "reminder_display": rem_disp,
            "actions": ["CREATE_MEETING", "CREATE_REMINDER"] if rem_disp else ["CREATE_MEETING"],
            "conflict_info": conflict_info,
        }

        return {
            "pending_confirmation": True,
            "pending_action": pending_action,
            "current_hcp_id": hcp_id,
            "current_hcp_name": doc_name,
            "current_hospital": hosp,
            "card_data": card_data,
            "response": prompt,
        }

    # 2. Handle Multi-Action Meeting Capture (Past Interaction)
    if intent in [INTENT_CAPTURE_MEETING, INTENT_CREATE_INTERACTION, INTENT_CREATE_HCP]:
        target_hcp = state.resolved_hcp
        if not target_hcp and und and und.doctor_name:
            match_res = match_hcp_from_db(db, und.doctor_name)
            if match_res.get("best_match"):
                target_hcp = match_res["best_match"]

        if not target_hcp or not target_hcp.get("doctor_name") or not is_valid_person_name(target_hcp.get("doctor_name")):
            if und and und.is_new_hcp:
                prompt = "డాక్టర్ పేరు ఏమిటి?" if is_te else "What is the doctor's name?"
                return {
                    "needs_clarification": True,
                    "clarification_type": "doctor_name_missing",
                    "response": prompt,
                    "pending_confirmation": False,
                    "pending_action": {
                        "type": INTENT_CAPTURE_MEETING,
                        "is_new_hcp": True,
                        "hospital": und.hospital,
                        "specialization": und.specialization,
                        "phone": und.phone,
                        "email": und.email,
                        "product": und.product,
                        "doctor_request": und.doctor_request,
                        "follow_up_display": und.follow_up_display,
                        "actions": ["CREATE_HCP", "CREATE_INTERACTION"],
                    }
                }

            cand_name = clean_doctor_name((und.doctor_name if und else None) or state.entity_name or "the doctor")
            prompt = (
                f"డాక్టర్ '{cand_name or 'డాక్టర్'}' CRM లో కనుగొనబడలేదు. కొత్త HCP గా add చేయమంటారా?"
                if is_te
                else f"I couldn't find '{cand_name or 'the doctor'}' in your HCP directory. Would you like me to add them as a new doctor?"
            )
            return {"needs_clarification": True, "clarification_type": "hcp_not_found", "response": prompt}

        is_new_hcp = target_hcp.get("id") is None or und.is_new_hcp
        doc_name = clean_doctor_name(target_hcp.get("doctor_name")) or "Doctor"
        hosp = target_hcp.get("hospital") or und.hospital or "Apollo Hospital"
        city = target_hcp.get("city") or "Visakhapatnam"
        spec = target_hcp.get("specialization") or und.specialization or "Cardiologist"
        phone = target_hcp.get("phone") or und.phone or "Not specified"
        email = target_hcp.get("email") or und.email or "Not specified"

        action_id = str(uuid.uuid4())[:8]
        actions_list = ["CREATE_HCP", "CREATE_INTERACTION"] if is_new_hcp else ["CREATE_INTERACTION"]
        if und and und.follow_up_date:
            actions_list.append("CREATE_FOLLOWUP")

        fu_disp = und.follow_up_display if und and und.follow_up_display else None
        prod = und.product if und and und.product else "Not specified"
        req = und.doctor_request if und and und.doctor_request else "None"

        pending_action = {
            "action_id": action_id,
            "type": INTENT_CAPTURE_MEETING,
            "is_new_hcp": is_new_hcp,
            "hcp_id": target_hcp.get("id"),
            "hcp_name": doc_name,
            "hospital": hosp,
            "city": city,
            "specialization": spec,
            "phone": phone,
            "email": email,
            "meeting_notes": und.meeting_summary or f"Meeting with {doc_name}.",
            "products_discussed": prod,
            "doctor_request": req,
            "follow_up_date": und.follow_up_date if und else None,
            "follow_up_display": fu_disp,
            "actions": actions_list,
        }

        fu_s_en = f" with a follow-up on {fu_disp}" if fu_disp else ""
        fu_s_te = f" ({fu_disp} న follow-up తో)" if fu_disp else ""
        prompt = (
            f"{doc_name} తో మీటింగ్‌ వివరాలు సమీక్షించండి{fu_s_te}. సేవ్ చేయమంటారా?"
            if is_te
            else f"Here is the meeting review for {doc_name} at {hosp}{fu_s_en}. Would you like me to confirm and save this to your CRM?"
        )

        card_data = {
            "type": "meeting_capture_confirmation",
            "action_id": action_id,
            "doctor_name": doc_name,
            "hospital": hosp,
            "city": city,
            "specialization": spec,
            "phone": phone,
            "email": email,
            "product": prod,
            "request": req,
            "follow_up_display": fu_disp,
            "actions": actions_list,
            "is_new_hcp": is_new_hcp,
            "evidence": state.transcript,
        }

        return {
            "pending_confirmation": True,
            "pending_action": pending_action,
            "current_hcp_id": target_hcp.get("id"),
            "current_hcp_name": doc_name,
            "current_hospital": hosp,
            "card_data": card_data,
            "response": prompt,
        }

    # 3. Handle Follow-Up Creation & Incremental Evolving Draft Merge
    if intent == INTENT_CREATE_FOLLOWUP:
        # If there is an existing pending meeting capture draft, merge follow-up into it
        if state.pending_action and state.pending_action.get("type") in [INTENT_CAPTURE_MEETING, "CAPTURE_MEETING"]:
            act = dict(state.pending_action)
            dt_disp = und.follow_up_display if und and und.follow_up_display else "next week"
            dt_val = und.follow_up_date if und and und.follow_up_date else (datetime.now() + timedelta(days=7)).isoformat()
            act["follow_up_date"] = dt_val
            act["follow_up_display"] = dt_disp
            if "CREATE_FOLLOWUP" not in act.get("actions", []):
                act["actions"] = list(act.get("actions", [])) + ["CREATE_FOLLOWUP"]

            prompt = (
                f"{act.get('hcp_name')} తో {dt_disp} న follow-up add చేశాను. సేవ్ చేయమంటారా?"
                if is_te
                else f"I've added a follow-up for {dt_disp} to the meeting with {act.get('hcp_name')}. Would you like me to confirm and save this?"
            )

            card_data = {
                "type": "meeting_capture_confirmation",
                "action_id": act.get("action_id"),
                "doctor_name": act.get("hcp_name"),
                "hospital": act.get("hospital"),
                "city": act.get("city"),
                "specialization": act.get("specialization"),
                "phone": act.get("phone", "Not specified"),
                "email": act.get("email", "Not specified"),
                "product": act.get("products_discussed") or act.get("product") or "Not specified",
                "request": act.get("doctor_request") or act.get("request") or "None",
                "follow_up_display": dt_disp,
                "actions": act.get("actions", []),
                "is_new_hcp": act.get("is_new_hcp", False),
            }

            return {
                "pending_confirmation": True,
                "pending_action": act,
                "card_data": card_data,
                "response": prompt,
            }

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
            target_hcp = {"id": state.current_hcp_id or 1, "doctor_name": state.current_hcp_name, "hospital": state.current_hospital or "Apollo Hospital"}

        if not target_hcp:
            prompt = "ఏ డాక్టర్‌తో follow-up షెడ్యూల్ చేయాలి?" if is_te else "Which doctor would you like to schedule the follow-up with?"
            return {"needs_clarification": True, "clarification_type": "hcp_missing", "response": prompt}

        doc_name = clean_doctor_name(target_hcp.get("doctor_name")) or "Doctor"
        dt_disp = und.follow_up_display if und and und.follow_up_display else "next week"
        dt_val = und.follow_up_date if und and und.follow_up_date else (datetime.now() + timedelta(days=7)).isoformat()

        action_id = str(uuid.uuid4())[:8]
        pending_action = {
            "action_id": action_id,
            "type": INTENT_CREATE_FOLLOWUP,
            "hcp_id": target_hcp.get("id", 1),
            "hcp_name": doc_name,
            "date": dt_val,
            "date_display": dt_disp,
            "notes": f"Follow-up with {doc_name}",
            "actions": ["CREATE_FOLLOWUP"],
        }

        prompt = (
            f"{doc_name} తో {dt_disp} న follow-up షెడ్యూల్ చేయమంటారా?"
            if is_te
            else f"Should I schedule a follow-up with {doc_name} for {dt_disp}?"
        )

        card_data = {
            "type": "confirmation_action",
            "action_id": action_id,
            "action_type": "CREATE_FOLLOWUP",
            "doctor_name": doc_name,
            "hospital": target_hcp.get("hospital", "Apollo Hospital"),
            "date_display": dt_disp,
            "actions": ["CREATE_FOLLOWUP"],
        }

        return {
            "pending_confirmation": True,
            "pending_action": pending_action,
            "current_hcp_id": target_hcp.get("id"),
            "current_hcp_name": doc_name,
            "current_hospital": target_hcp.get("hospital"),
            "card_data": card_data,
            "response": prompt,
        }

    # 4. Handle Conversational Corrections & Context Override
    if (state.is_override or (und and und.is_override)) and not state.pending_action:
        doc_name = state.current_hcp_name or (und.override_target if und else None)
        return {
            "current_hcp_id": state.current_hcp_id,
            "current_hcp_name": doc_name,
            "current_hospital": state.current_hospital,
            "pending_confirmation": False,
            "pending_action": None,
            "response": f"Understood, I've updated your active doctor context to {doc_name}."
        }

    if intent == INTENT_CORRECT_PENDING_ACTION and state.pending_action:
        act = dict(state.pending_action)
        corrs = und.corrections if und else {}
        changes_applied = list(act.get("changes_applied", []))

        is_schedule = act.get("type") == "SCHEDULE_MEETING"

        if is_schedule:
            # Handle Meeting Schedule corrections
            if corrs.get("change_time") or und.meeting_time_display:
                t_val = corrs.get("change_time") or und.meeting_time_display
                act["meeting_time_display"] = t_val
                changes_applied.append(f"Time: {t_val}")

            if corrs.get("change_date") or und.follow_up_display:
                d_val = corrs.get("change_date") or und.follow_up_display
                act["meeting_date_display"] = d_val
                changes_applied.append(f"Date: {d_val}")

            if corrs.get("remove_reminder") or (und and (und.reminder_minutes == 0 or und.reminder_display == "No reminder")):
                act["reminder_display"] = "No reminder"
                act["reminder_minutes"] = 0
                act["actions"] = [a for a in act.get("actions", []) if a != "CREATE_REMINDER"]
                changes_applied.append("Removed reminder")
            elif corrs.get("change_reminder") or (und and und.reminder_display):
                r_val = corrs.get("change_reminder") or und.reminder_display
                rem_m = und.reminder_minutes if und and und.reminder_minutes is not None else 30
                act["reminder_display"] = r_val
                act["reminder_minutes"] = rem_m
                if "CREATE_REMINDER" not in act.get("actions", []):
                    act["actions"] = list(act.get("actions", [])) + ["CREATE_REMINDER"]
                changes_applied.append(f"Reminder: {r_val}")

            if corrs.get("change_doctor") or und.doctor_name:
                doc_m = corrs.get("change_doctor") or und.doctor_name
                m_res = match_hcp_from_db(db, doc_m)
                if m_res.get("best_match"):
                    b = m_res["best_match"]
                    act["hcp_id"] = b["id"]
                    act["hcp_name"] = b["doctor_name"]
                    act["hospital"] = b.get("hospital")
                    changes_applied.append(f"Doctor: {b['doctor_name']}")

            act["changes_applied"] = changes_applied
            m_dt = act.get('meeting_date_display') or act.get('date_display') or 'Friday'
            m_tm = act.get('meeting_time_display') or '03:00 PM'

            prompt = (
                f"సరే, {act.get('hcp_name')} తో meeting వివరాలు అప్‌డేట్ చేశాను ({m_dt} {m_tm}). షెడ్యూల్ చేయమంటారా?"
                if is_te
                else f"I've updated the meeting with {act.get('hcp_name')} to {m_dt} at {m_tm} ({act.get('reminder_display', 'No reminder')}). Would you like me to confirm and schedule this?"
            )

            card_data = {
                "type": "meeting_schedule_confirmation",
                "action_id": act.get("action_id"),
                "doctor_name": act.get("hcp_name"),
                "hospital": act.get("hospital"),
                "city": act.get("city"),
                "specialization": act.get("specialization"),
                "meeting_date_display": act.get("meeting_date_display"),
                "meeting_time_display": act.get("meeting_time_display"),
                "location": act.get("location"),
                "reminder_display": act.get("reminder_display"),
                "actions": act.get("actions", ["CREATE_MEETING"]),
                "changes_applied": changes_applied,
                "conflict_info": act.get("conflict_info"),
            }

            return {
                "pending_confirmation": True,
                "pending_action": act,
                "card_data": card_data,
                "response": prompt,
            }

        else:
            # Handle Interaction / Follow-up / Incremental HCP additions
            if corrs.get("change_doctor") or (und and und.doctor_name and is_valid_person_name(und.doctor_name)):
                doc_m = corrs.get("change_doctor") or und.doctor_name
                m_res = match_hcp_from_db(db, doc_m)
                if m_res.get("best_match"):
                    b = m_res["best_match"]
                    act["hcp_id"] = b["id"]
                    act["hcp_name"] = b["doctor_name"]
                    act["hospital"] = b.get("hospital")
                    act["is_new_hcp"] = False
                    changes_applied.append(f"Doctor: {b['doctor_name']}")
                else:
                    c_name = clean_doctor_name(doc_m)
                    act["hcp_name"] = c_name
                    act["doctor_name"] = c_name
                    act["is_new_hcp"] = True
                    changes_applied.append(f"Doctor: {c_name}")

            if und and und.hospital:
                act["hospital"] = und.hospital
                changes_applied.append(f"Hospital: {und.hospital}")

            if und and und.specialization:
                act["specialization"] = und.specialization
                changes_applied.append(f"Specialization: {und.specialization}")

            if und and und.city:
                act["city"] = und.city
                changes_applied.append(f"City: {und.city}")

            if und and und.phone:
                act["phone"] = und.phone
                changes_applied.append(f"Phone: {und.phone}")

            if und and und.email:
                act["email"] = und.email
                changes_applied.append(f"Email: {und.email}")

            if corrs.get("change_product") or (und and und.product):
                p_val = corrs.get("change_product") or und.product
                act["products_discussed"] = p_val
                act["product"] = p_val
                changes_applied.append(f"Product: {p_val}")

            if corrs.get("change_request") or (und and und.doctor_request):
                r_val = corrs.get("change_request") or und.doctor_request
                act["doctor_request"] = r_val
                act["request"] = r_val
                changes_applied.append(f"Request: {r_val}")

            if corrs.get("remove_follow_up"):
                act["follow_up_display"] = None
                act["follow_up_date"] = None
                act["actions"] = [a for a in act.get("actions", []) if a != "CREATE_FOLLOWUP"]
                changes_applied.append("Removed follow-up")
            elif corrs.get("change_follow_up") or (und and und.follow_up_display and not und.meeting_time_display and act.get("type") != "SCHEDULE_MEETING"):
                fu_val = corrs.get("change_follow_up") or und.follow_up_display
                act["follow_up_display"] = fu_val
                act["follow_up_date"] = und.follow_up_date if und else None
                if "CREATE_FOLLOWUP" not in act.get("actions", []):
                    act["actions"] = list(act.get("actions", [])) + ["CREATE_FOLLOWUP"]
                changes_applied.append(f"Follow-up: {fu_val}")

            if corrs.get("change_time") or (und and und.meeting_time_display):
                t_val = corrs.get("change_time") or und.meeting_time_display
                act["meeting_time_display"] = t_val
                act["type"] = "SCHEDULE_MEETING"
                if "CREATE_MEETING" not in act.get("actions", []):
                    act["actions"] = list(act.get("actions", [])) + ["CREATE_MEETING"]
                changes_applied.append(f"Time: {t_val}")

            if (corrs.get("change_date") or (und and und.follow_up_display)) and (act.get("type") == "SCHEDULE_MEETING" or intent == INTENT_SCHEDULE_MEETING or und.meeting_time_display):
                d_val = corrs.get("change_date") or und.follow_up_display
                act["meeting_date_display"] = d_val
                act["type"] = "SCHEDULE_MEETING"
                if "CREATE_MEETING" not in act.get("actions", []):
                    act["actions"] = list(act.get("actions", [])) + ["CREATE_MEETING"]
                changes_applied.append(f"Date: {d_val}")

            if corrs.get("remove_reminder") or (und and (und.reminder_minutes == 0 or und.reminder_display == "No reminder")):
                act["reminder_display"] = "No reminder"
                act["reminder_minutes"] = 0
                act["actions"] = [a for a in act.get("actions", []) if a != "CREATE_REMINDER"]
                changes_applied.append("Removed reminder")
            elif corrs.get("change_reminder") or (und and und.reminder_display):
                r_val = corrs.get("change_reminder") or und.reminder_display
                rem_m = und.reminder_minutes if und and und.reminder_minutes is not None else 30
                act["reminder_display"] = r_val
                act["reminder_minutes"] = rem_m
                if "CREATE_REMINDER" not in act.get("actions", []):
                    act["actions"] = list(act.get("actions", [])) + ["CREATE_REMINDER"]
                changes_applied.append(f"Reminder: {r_val}")

            act["changes_applied"] = changes_applied

            prompt = (
                f"వివరాలు అప్‌డేట్ చేశాను ({', '.join(changes_applied[-2:])}). సేవ్ చేయమంటారా?"
                if is_te
                else f"I've updated the review with those changes. Would you like me to confirm and save this?"
            )

            card_data = {
                "type": "meeting_capture_confirmation" if act.get("type") == INTENT_CAPTURE_MEETING else "confirmation_action",
                "action_id": act.get("action_id"),
                "doctor_name": act.get("hcp_name"),
                "hospital": act.get("hospital"),
                "city": act.get("city"),
                "specialization": act.get("specialization"),
                "phone": act.get("phone", "Not specified"),
                "email": act.get("email", "Not specified"),
                "product": act.get("products_discussed") or act.get("product") or "Not specified",
                "request": act.get("doctor_request") or act.get("request") or "None",
                "follow_up_display": act.get("follow_up_display"),
                "date_display": act.get("follow_up_display") or act.get("date_display"),
                "actions": act.get("actions", []),
                "changes_applied": changes_applied,
                "is_new_hcp": act.get("is_new_hcp", False),
            }

            return {
                "pending_confirmation": True,
                "pending_action": act,
                "card_data": card_data,
                "response": prompt,
            }

    return {}


def execute_crm_tool(state: VoiceCopilotState) -> dict:
    global _CURRENT_DB
    db = _CURRENT_DB
    intent = state.intent
    und = state.understanding
    is_te = state.language in ["te", "mixed"]

    # 1. Handle Confirmation of Pending Action (ATOMIC TRANSACTION COMMIT)
    if intent == INTENT_CONFIRM_ACTION and state.pending_action:
        action = state.pending_action
        act_id = action.get("action_id")

        # Idempotency Check
        if act_id and act_id in EXECUTED_ACTION_IDS:
            card_type = "meeting_schedule_card" if action.get("type") == "SCHEDULE_MEETING" else "meeting_capture_card"
            card_data = {
                "type": card_type,
                "doctor_name": action.get("hcp_name"),
                "hospital": action.get("hospital"),
                "meeting_date_display": action.get("meeting_date_display"),
                "meeting_time_display": action.get("meeting_time_display"),
                "follow_up_display": action.get("follow_up_display"),
                "status": "completed",
                "is_completed": True,
            }
            return {
                "pending_confirmation": False,
                "pending_action": None,
                "card_data": card_data,
                "response": "This action was already confirmed and saved.",
                "tool_result": {"type": "idempotent_noop", "status": "completed"}
            }

        # Execute Atomic DB Transaction
        tx_res = execute_atomic_crm_transaction(db, action, user_id=state.user_id)

        if not tx_res.get("success"):
            logger.error(f"[VoiceCopilot] Atomic transaction failed: {tx_res.get('error')}")
            return {
                "pending_confirmation": False,
                "pending_action": None,
                "response": "I encountered an issue saving your request to the database. Please try again.",
                "error": tx_res.get("error"),
            }

        if act_id:
            EXECUTED_ACTION_IDS.add(act_id)

        # Build Completed Card
        is_schedule = action.get("type") == "SCHEDULE_MEETING"
        card_type = "meeting_schedule_card" if is_schedule else "meeting_capture_card"
        card_data = {
            "type": card_type,
            "doctor_name": action.get("hcp_name"),
            "hospital": action.get("hospital"),
            "city": action.get("city"),
            "specialization": action.get("specialization"),
            "meeting_date_display": action.get("meeting_date_display"),
            "meeting_time_display": action.get("meeting_time_display"),
            "location": action.get("location"),
            "reminder_display": action.get("reminder_display"),
            "follow_up_display": action.get("follow_up_display"),
            "status": "completed",
            "is_completed": True,
        }

        # Success Response Generation
        doc_n = action.get("hcp_name", "Doctor")
        if is_schedule:
            m_dt = action.get("meeting_date_display", "the scheduled date")
            m_tm = action.get("meeting_time_display", "the scheduled time")
            resp = (
                f"సరే! {doc_n} తో {m_dt} న {m_tm} కి meeting విజయవంతంగా షెడ్యూల్ చేయబడింది."
                if is_te
                else f"Done. I have scheduled the meeting with {doc_n} for {m_dt} at {m_tm}."
            )
        else:
            fu_d = action.get("follow_up_display")
            fu_s = f" and scheduled the follow-up for {fu_d}" if fu_d and fu_d != "None" else ""
            resp = (
                f"సరే! {doc_n} తో మీటింగ్‌ వివరాలు సేవ్ చేయబడ్డాయి."
                if is_te
                else f"Done. I logged the interaction with {doc_n}{fu_s}."
            )

        return {
            "pending_confirmation": False,
            "pending_action": None,
            "current_hcp_id": tx_res.get("created_entities", {}).get("hcp_id") or action.get("hcp_id"),
            "current_hcp_name": action.get("hcp_name"),
            "card_data": card_data,
            "response": resp,
            "tool_result": tx_res,
        }

    # 2. Handle Cancellation of Pending Action
    if intent == INTENT_CANCEL_ACTION:
        return {
            "pending_confirmation": False,
            "pending_action": None,
            "response": "సరే, రద్దు చేశాను. సేవ్ చేయలేదు." if is_te else "Cancelled. No changes were saved to your CRM.",
            "tool_result": {"type": "cancelled"}
        }

    # 3. Read Operations
    hcp_id = state.current_hcp_id or (state.resolved_hcp.get("id") if state.resolved_hcp else None)
    doc_name = state.current_hcp_name or (state.resolved_hcp.get("doctor_name") if state.resolved_hcp else None)

    if intent == INTENT_GET_HCP_DETAILS and hcp_id:
        hcp = get_hcp_details(db, hcp_id)
        if hcp:
            return {"tool_result": {"type": "hcp_details", "data": hcp}}

    if intent == INTENT_GET_HCP_INTERACTIONS and hcp_id:
        inters = get_hcp_interactions(db, hcp_id=hcp_id, limit=5)
        return {"tool_result": {"type": "hcp_interactions", "doctor_name": doc_name, "interactions": inters}}

    if intent == INTENT_GET_HCP_FOLLOWUPS and hcp_id:
        fus = get_hcp_followups(db, hcp_id)
        return {"tool_result": {"type": "hcp_followups", "doctor_name": doc_name, "followups": fus}}

    if intent == INTENT_GET_ALL_FOLLOWUPS:
        fus = get_all_followups(db, user_id=state.user_id, time_filter="all")
        return {"tool_result": {"type": "all_followups", "followups": fus}}

    if intent == INTENT_GET_RECENT_INTERACTIONS:
        inters = get_recent_interactions(db, user_id=state.user_id, limit=5)
        return {"tool_result": {"type": "recent_interactions", "interactions": inters}}

    if intent == INTENT_GET_PRODUCT_DISCUSSIONS and (state.entity_product or (und and und.product)):
        prod = state.entity_product or (und.product if und else "")
        prods = get_product_discussions(db, prod, user_id=state.user_id)
        return {"tool_result": {"type": "product_discussions", "product": prod, "records": prods}}

    if intent == INTENT_GET_HOSPITAL_DETAILS and (state.entity_hospital or (und and und.hospital)):
        hosp = state.entity_hospital or (und.hospital if und else "")
        docs = get_hospital_doctors(db, hospital_name=hosp)
        return {"tool_result": {"type": "hospital_doctors", "hospital": hosp, "doctors": docs}}

    if intent == INTENT_GET_CRM_BRIEF:
        brief = get_crm_day_brief(db, user_id=state.user_id)
        return {"tool_result": {"type": "crm_brief", "brief": brief}}

    if intent == INTENT_GET_NEXT_ACTION:
        action_data = get_next_action(db, user_id=state.user_id)
        return {"tool_result": {"type": "next_action", "next_action": action_data}}

    if intent == INTENT_GET_PRE_MEETING_INTELLIGENCE and hcp_id:
        intel = get_pre_meeting_intelligence(db, hcp_id=hcp_id)
        return {"tool_result": {"type": "pre_meeting_intelligence", "intelligence": intel}}

    if intent == INTENT_GET_CRM_ANALYTICS:
        metric = und.analytics_metric if und and und.analytics_metric else "weekly_meetings"
        analytics = get_crm_analytics(db, user_id=state.user_id, metric=metric)
        return {"tool_result": {"type": "crm_analytics", "analytics": analytics, "metric": metric}}

    if intent == INTENT_SEARCH_HCP:
        q = (und.doctor_name if und and und.doctor_name else None) or state.normalized_transcript or state.transcript
        matches = search_hcps(db, q)
        return {"tool_result": {"type": "search_results", "query": q, "results": matches}}

    return {}


def validate_and_format(state: VoiceCopilotState) -> dict:
    if state.card_data:
        return {}

    res = state.tool_result
    if not res:
        return {}

    r_type = res.get("type")

    if r_type == "hcp_details":
        return {"card_data": {"type": "hcp_card", **res.get("data", {})}}

    if r_type == "hcp_interactions":
        return {"card_data": {"type": "interaction_card", "doctor_name": res.get("doctor_name"), "interactions": res.get("interactions", [])}}

    if r_type == "hcp_followups" or r_type == "all_followups":
        return {"card_data": {"type": "followups_list_card", "followups": res.get("followups", [])}}

    if r_type == "recent_interactions":
        return {"card_data": {"type": "recent_interactions_card", "interactions": res.get("interactions", [])}}

    if r_type == "product_discussions":
        return {"card_data": {"type": "product_discussions_card", "product": res.get("product"), "records": res.get("records", [])}}

    if r_type == "hospital_doctors":
        return {"card_data": {"type": "hospital_doctors_card", "hospital": res.get("hospital"), "doctors": res.get("doctors", [])}}

    if r_type == "crm_brief":
        return {"card_data": {"type": "crm_brief_card", "brief": res.get("brief", {})}}

    if r_type == "next_action":
        return {"card_data": {"type": "next_action_card", "next_action": res.get("next_action", {})}}

    if r_type == "pre_meeting_intelligence":
        return {"card_data": {"type": "pre_meeting_intel_card", "hcp": state.resolved_hcp, "intelligence": res.get("intelligence", {})}}

    if r_type == "crm_analytics":
        return {"card_data": {"type": "analytics_card", "analytics": res.get("analytics", {}), "metric": res.get("metric")}}

    return {}


def generate_response(state: VoiceCopilotState) -> dict:
    if state.response:
        return {}

    is_te = state.language in ["te", "mixed"]

    if state.needs_clarification and state.clarification_type == "ambiguity":
        cands = state.ambiguous_candidates
        names = [f"{c.get('doctor_name')} ({c.get('hospital')})" for c in cands]
        joined = ", ".join(names)
        resp = (
            f"నేను బహుళ వైద్యులను కనుగొన్నాను: {joined}. మీరు ఎవరిని ఉద్దేశించారు?"
            if is_te
            else f"I found multiple HCPs matching that name: {joined}. Which doctor did you mean?"
        )
        return {
            "response": resp,
            "card_data": {"type": "ambiguity_card", "candidates": cands}
        }

    res = state.tool_result
    if not res:
        und = state.understanding
        if und and und.conversational_reply:
            return {"response": und.conversational_reply}
        if state.intent == INTENT_GET_CRM_BRIEF:
            return {"response": "Here is your daily CRM briefing. You're clear today with no pending tasks."}
        if state.intent == INTENT_GET_NEXT_ACTION:
            return {"response": "You're up to date! No urgent overdue follow-ups or pending requests."}
        return {"response": "నమస్కారం! మీ డాక్టర్ సమావేశాలు లేదా టెరిటరీ పనుల్లో ఎలా సహాయపడగలను?" if is_te else "Hello! How can I assist with your territory, doctor visits, or scheduled meetings today?"}

    r_type = res.get("type")

    # Dynamic LLM Tool Result Synthesis
    from app.ai.reasoning_engine import reasoning_engine
    if r_type not in ["cancelled", "confirmed", "meeting_saved"]:
        synth = reasoning_engine.synthesize_tool_response(
            user_query=state.transcript,
            tool_name=r_type,
            tool_result=res,
            context={"current_hcp_name": state.current_hcp_name},
            language=state.language
        )
        if synth:
            return {"response": synth}

    if r_type == "hcp_details":
        h = res.get("data", {})
        d_name = h.get("doctor_name", "Doctor")
        hosp = h.get("hospital", "Hospital")
        city = h.get("city", "")
        spec = h.get("specialization", "")
        loc = f" in {city}" if city else ""
        sp = f" as a {spec}" if spec else ""
        return {"response": f"{d_name} works at {hosp}{loc}{sp}."}

    if r_type == "hcp_interactions":
        inters = res.get("interactions", [])
        d_name = res.get("doctor_name", "Doctor")
        if not inters:
            return {"response": f"No past interactions recorded for {d_name}."}
        last_i = inters[0]
        dt = (last_i.get("created_at") or "")[:10]
        prods = last_i.get("products_discussed") or "General relationship"
        return {"response": f"You last met {d_name} on {dt}. Products discussed: {prods}."}

    if r_type == "hcp_followups" or r_type == "all_followups":
        fus = res.get("followups", [])
        if not fus:
            return {"response": "No scheduled follow-ups found."}
        return {"response": f"You have {len(fus)} scheduled follow-up(s)."}

    if r_type == "crm_brief":
        b = res.get("brief", {})
        tm_cnt = b.get("today_meetings_count", 0)
        tf_cnt = b.get("today_followups_count", 0)
        od_cnt = b.get("overdue_followups_count", 0)
        if tm_cnt == 0 and tf_cnt == 0 and od_cnt == 0:
            return {"response": "You're clear today! No scheduled meetings, follow-ups, or overdue tasks on your calendar."}
        return {"response": f"Here is your daily brief: {tm_cnt} meeting(s) today, {tf_cnt} follow-up(s), and {od_cnt} overdue task(s)."}

    if r_type == "next_action":
        na = res.get("next_action", {})
        return {"response": na.get("explanation") or "Here is your next recommended action."}

    if r_type == "product_discussions":
        prod = res.get("product", "Product")
        recs = res.get("records", [])
        if not recs:
            return {"response": f"No recorded discussions found for {prod}."}
        names = [r.get("hcp_name") for r in recs if r.get("hcp_name")]
        return {"response": f"You discussed {prod} with: {', '.join(names[:3])}."}

    if r_type == "hospital_doctors":
        hosp = res.get("hospital", "Hospital")
        docs = res.get("doctors", [])
        if not docs:
            return {"response": f"No doctors found for {hosp} in your territory."}
        names = [d.get("doctor_name") for d in docs]
        return {"response": f"Doctors at {hosp}: {', '.join(names)}."}

    if r_type == "search_results":
        results = res.get("results", [])
        if not results:
            return {"response": "No matching doctors found in your HCP directory."}
        names = [r.get("doctor_name") for r in results]
        return {"response": f"Found: {', '.join(names)}."}

    return {"response": "I've processed your CRM request."}


# Build LangGraph workflow
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
    current_hospital: Optional[str] = None,
    pending_confirmation: bool = False,
    pending_action: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    preferred_provider: Optional[str] = None,
) -> Dict[str, Any]:
    global _CURRENT_DB
    _CURRENT_DB = db

    initial_state = VoiceCopilotState(
        user_id=user_id,
        transcript=transcript,
        history=history or [],
        current_hcp_id=current_hcp_id,
        current_hcp_name=current_hcp_name,
        current_hospital=current_hospital,
        pending_confirmation=pending_confirmation,
        pending_action=pending_action,
        preferred_provider=preferred_provider,
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
