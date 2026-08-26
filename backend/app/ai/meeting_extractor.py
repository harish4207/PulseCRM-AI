"""
meeting_extractor.py - Natural Multi-Action Meeting Information Extraction & Evidence Gathering.

Handles:
- Structured extraction: HCP, Hospital, Meeting Date, Products, Requests, Follow-up
- Strict distinction between Interaction-only vs Interaction + Follow-up
- Source evidence extraction for full auditability
- Natural language meeting corrections across conversational turns
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    "సెప్టెంబర్": 9, "సెప్టెంబరు": 9, "అక్టోబర్": 10, "ఆగస్టు": 8, "నవంబర్": 11, "డిసెంబర్": 12
}

DAY_MAP = {
    "monday": 0, "somavaram": 0, "సోమవారం": 0,
    "tuesday": 1, "mangalavaram": 1, "మంగళవారం": 1,
    "wednesday": 2, "budhavaram": 2, "బుధవారం": 2,
    "thursday": 3, "guruvaram": 3, "గురువారం": 3,
    "friday": 4, "sukravaram": 4, "శుక్రవారం": 4,
    "saturday": 5, "sanivaram": 5, "శనివారం": 5,
    "sunday": 6, "adivaram": 6, "ఆదివారం": 6,
}

KNOWN_PRODUCTS = ["CardioPress", "CardioPress-50", "CardioPress-75", "CardioPress-100", "AmloPulse", "GlycoCare", "NeuroCalm", "LipidGuard", "RespiClear"]


def parse_date_expression(text: str) -> Optional[Tuple[datetime, str, str]]:
    if not text:
        return None

    now = datetime.now()
    norm = text.lower().strip()

    # 1. Month Day (e.g. October 1, September 29, Sep 29, 29th September)
    m_match = re.search(r"\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec|సెప్టెంబర్|సెప్టెంబరు|అక్టోబర్|ఆగస్టు)\s+(\d{1,2})(?:st|nd|rd|th)?\b", norm, re.IGNORECASE)
    if not m_match:
        m_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec|సెప్టెంబర్|సెప్టెంబరు|అక్టోబర్|ఆగస్టు)\b", norm, re.IGNORECASE)
        if m_match:
            day_val = int(m_match.group(1))
            month_str = m_match.group(2)
            evidence = m_match.group(0)
        else:
            day_val = None
            month_str = None
            evidence = ""
    else:
        month_str = m_match.group(1)
        day_val = int(m_match.group(2))
        evidence = m_match.group(0)

    if month_str and day_val and 1 <= day_val <= 31:
        month_val = MONTH_MAP.get(month_str.lower(), 9)
        year_val = now.year
        target = datetime(year_val, month_val, day_val, 10, 0, 0)
        t_match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", norm, re.IGNORECASE)
        if t_match:
            hr = int(t_match.group(1))
            mn = int(t_match.group(2) or 0)
            ampm = (t_match.group(3) or "").lower()
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0
            target = target.replace(hour=hr, minute=mn)
            evidence += f" {t_match.group(0)}"

        return target, target.strftime("%B %d, %Y"), evidence.strip()

    # 2. Day of Week (e.g. next Monday, next Friday, sukravaram, somavaram)
    for day_name, day_idx in DAY_MAP.items():
        if day_name in norm:
            days_ahead = (day_idx - now.weekday() + 7) % 7
            if days_ahead == 0 or "next" in norm or "వచ్చే" in norm:
                days_ahead = days_ahead + 7 if days_ahead <= 0 else days_ahead
            target = now + timedelta(days=days_ahead)
            target = target.replace(hour=10, minute=0, second=0, microsecond=0)
            ev = f"next {day_name}" if "next" in norm else day_name
            return target, target.strftime("%B %d, %Y"), ev

    # 3. Tomorrow / Repu
    if "tomorrow" in norm or "repu" in norm or "రేపు" in norm:
        target = now + timedelta(days=1)
        target = target.replace(hour=10, minute=0, second=0, microsecond=0)
        return target, target.strftime("%B %d, %Y"), "tomorrow"

    # 4. Next week / Next month
    if "next week" in norm or "vachhe vaaram" in norm:
        target = now + timedelta(days=7)
        target = target.replace(hour=10, minute=0, second=0, microsecond=0)
        return target, target.strftime("%B %d, %Y"), "next week"

    if "next month" in norm or "vachhe nela" in norm:
        target = now + timedelta(days=30)
        target = target.replace(hour=10, minute=0, second=0, microsecond=0)
        return target, target.strftime("%B %d, %Y"), "next month"

    # 5. Today / Ivala
    if "today" in norm or "ivala" in norm or "ఈరోజు" in norm:
        target = now.replace(hour=10, minute=0, second=0, microsecond=0)
        return target, target.strftime("%B %d, %Y"), "today"

    return None


def extract_request_action(transcript: str) -> Tuple[Optional[str], Optional[str]]:
    patterns = [
        r"([A-Za-z0-9\s\-]+(?:brochure|samples|catalog|document|file|information|data|samples|brochures))\s+(?:pampinchamani|pampamani|adigindi|adigaru)",
        r"(?:asked(?: me)? to|asked for|requested|adigindi|adigaru|pampinchamani)\s+([^.\n,]+)",
        r"(?:send|pampali|share)\s+(?:the\s+)?([A-Za-z0-9\s\-]+(?:brochure|samples|catalog|document|file|information|data))",
        r"(?:interested in|meeda interest)\s+[^.\n,]+(?:and\s+asked(?: me)? to|and asked for)\s+([^.\n,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            clean = m.group(1).strip()
            clean = re.split(r"\s+(?:follow up|follow-up|and|on|september|save)\b", clean, flags=re.IGNORECASE)[0]
            if len(clean) > 3 and clean.lower() not in ["adigindi", "adigaru"]:
                return clean.strip(), m.group(0).strip()
    return None, None


def extract_meeting_details(transcript: str, known_product: Optional[str] = None) -> Dict[str, Any]:
    norm = transcript.lower()

    # 1. Product extraction & evidence
    product = known_product
    product_ev = None
    if not product:
        prod_matches = re.finditer(r"\b(CardioPress(?:-(?:50|75|100))?|AmloPulse|GlycoCare|NeuroCalm|LipidGuard|RespiClear)\b", transcript, re.IGNORECASE)
        for pm in prod_matches:
            product = pm.group(1)
            start = max(0, pm.start() - 15)
            end = min(len(transcript), pm.end() + 15)
            product_ev = transcript[start:end].strip()
            break

    # 2. Doctor Request extraction & evidence
    request_str, request_ev = extract_request_action(transcript)

    # 3. Follow-up distinction & parsing
    has_followup_intent = any(k in norm for k in [
        "follow up", "follow-up", "followup", "meet again", "malli kalavali",
        "pettali", "schedule", "next friday", "next monday", "next week"
    ]) or bool(re.search(r"\b(?:follow up|meet again|on)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|sep|oct|nov|dec)\b", norm))

    fu_parsed = parse_date_expression(transcript) if has_followup_intent else None
    follow_up_date = fu_parsed[0] if fu_parsed else None
    follow_up_display = fu_parsed[1] if fu_parsed else None
    follow_up_ev = fu_parsed[2] if fu_parsed else None

    # 4. Planned actions: Strictly distinguish interaction only vs interaction + follow-up
    planned_actions = ["CREATE_INTERACTION"]
    if has_followup_intent and follow_up_date:
        planned_actions.append("CREATE_FOLLOWUP")

    # 5. Meeting notes synthesis
    notes_parts = ["Meeting logged via Voice Copilot."]
    if product:
        notes_parts.append(f"Discussed product: {product}.")
    if request_str:
        notes_parts.append(f"Doctor request: {request_str}.")
    if follow_up_display and "CREATE_FOLLOWUP" in planned_actions:
        notes_parts.append(f"Follow-up scheduled for {follow_up_display}.")

    meeting_notes = " ".join(notes_parts)

    evidence = {}
    if product_ev:
        evidence["product"] = product_ev
    if request_ev:
        evidence["request"] = request_ev
    if follow_up_ev:
        evidence["follow_up"] = follow_up_ev

    return {
        "action_id": str(uuid.uuid4())[:8],
        "product": product,
        "request": request_str,
        "follow_up_date": follow_up_date,
        "follow_up_display": follow_up_display,
        "planned_actions": planned_actions,
        "meeting_notes": meeting_notes,
        "evidence": evidence,
    }


def apply_meeting_correction(
    pending_action: Dict[str, Any],
    correction_text: str,
    db_hcps: Optional[List[Any]] = None
) -> Tuple[Dict[str, Any], List[str]]:
    updated = dict(pending_action)
    norm = correction_text.lower()
    changes = []

    # 1. Removal of Follow-up
    if any(k in norm for k in ["no follow up", "no follow-up", "no followup", "remove the follow-up", "remove follow up", "there was no follow-up", "follow up vaddu", "follow-up avasaram ledu"]):
        updated["follow_up_date"] = None
        updated["follow_up_display"] = None
        if "CREATE_FOLLOWUP" in updated.get("actions", []):
            updated["actions"] = [a for a in updated["actions"] if a != "CREATE_FOLLOWUP"]
        changes.append("Removed follow-up")

    # 2. Follow-up date modification (e.g. "Change the follow-up to October 1")
    elif any(k in norm for k in ["follow up to", "follow-up to", "change the follow", "reschedule to", "date to", "october", "september", "november", "december"]):
        parsed = parse_date_expression(correction_text)
        if parsed:
            updated["follow_up_date"] = parsed[0].isoformat()
            updated["follow_up_display"] = parsed[1]
            if "CREATE_FOLLOWUP" not in updated.get("actions", []):
                updated["actions"] = updated.get("actions", []) + ["CREATE_FOLLOWUP"]
            changes.append(f"Updated follow-up date to {parsed[1]}")

    # 3. Product modification (e.g. "The product was CardioPress-75, not CardioPress-50")
    prod_match = re.search(r"\b(CardioPress(?:-(?:50|75|100))?|AmloPulse|GlycoCare|NeuroCalm|LipidGuard|RespiClear)\b", correction_text, re.IGNORECASE)
    if prod_match:
        new_prod = prod_match.group(1)
        updated["products_discussed"] = new_prod
        changes.append(f"Updated product to {new_prod}")

    # 4. HCP / Doctor modification (e.g. "Actually it was Dr Sharma", "Rajesh doctor kaadu Sharma doctor")
    hcp_match = re.search(r"(?:actually\s+the\s+doctor\s+was|actually\s+it\s+was|doctor\s+was|doctor\s+is|hcp\s+was|kaadu|kadu|change\s+doctor\s+to|doctor\s+name\s+is)\s+(?:dr\.?\s+)?([A-Za-z\s]+)", correction_text, re.IGNORECASE)
    if hcp_match:
        cand_name = hcp_match.group(1).strip()
        cand_name = re.split(r"\s+(?:not|instead|and)\b", cand_name, flags=re.IGNORECASE)[0].strip()
        cand_name = re.sub(r"\b(doctor|garu|ni|tho|ki|lo)\b", "", cand_name, flags=re.IGNORECASE).strip()
        if len(cand_name) >= 3 and not any(p.lower() in cand_name.lower() for p in KNOWN_PRODUCTS):
            if db_hcps:
                from app.ai.fuzzy_matcher import calculate_similarity
                best_hcp = None
                best_s = 0.0
                for h in db_hcps:
                    s = calculate_similarity(cand_name, h.doctor_name)
                    if s > best_s:
                        best_s = s
                        best_hcp = h
                if best_hcp and best_s >= 0.6:
                    updated["hcp_id"] = best_hcp.id
                    updated["hcp_name"] = best_hcp.doctor_name
                    updated["hospital"] = best_hcp.hospital
                    changes.append(f"Changed HCP to {best_hcp.doctor_name} ({best_hcp.hospital})")
            else:
                updated["hcp_name"] = f"Dr. {cand_name.title()}"
                changes.append(f"Changed HCP to Dr. {cand_name.title()}")

    # 5. Request modification (e.g. "She asked for clinical information, not a brochure")
    if any(k in norm for k in ["asked for", "clinical information", "not a brochure", "request was"]):
        req_match = re.search(r"(?:asked for|request was|asked to)\s+([^,.\n]+)", correction_text, re.IGNORECASE)
        if req_match:
            new_req = req_match.group(1).strip()
            new_req = re.split(r"\s+(?:not|instead|and)\b", new_req, flags=re.IGNORECASE)[0]
            updated["request"] = new_req
            changes.append(f"Updated request to '{new_req}'")

    # Re-synthesize meeting notes
    notes_parts = ["Meeting logged via Voice Copilot."]
    if updated.get("products_discussed"):
        notes_parts.append(f"Discussed product: {updated['products_discussed']}.")
    if updated.get("request"):
        notes_parts.append(f"Doctor request: {updated['request']}.")
    if updated.get("follow_up_display") and "CREATE_FOLLOWUP" in updated.get("actions", []):
        notes_parts.append(f"Follow-up scheduled for {updated['follow_up_display']}.")
    updated["meeting_notes"] = " ".join(notes_parts)

    return updated, changes

# ---------------------------------------------------------------------------
# Phase 19: Time Parsing, Reminders & Dedicated Meeting Scheduling
# ---------------------------------------------------------------------------

def parse_time_expression(text: str) -> Optional[Tuple[int, int, str, str]]:
    if not text:
        return None

    norm = text.lower().strip()

    # 1. Explicit AM/PM (e.g., '3 PM', '3:30 PM', '11:00 AM', '11 AM', 'at 4 PM', 'at 3')
    t_match = re.search(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", norm, re.IGNORECASE)
    if t_match:
        hr = int(t_match.group(1))
        mn = int(t_match.group(2) or 0)
        ampm = t_match.group(3).lower()
        if ampm == "pm" and hr < 12:
            hr += 12
        elif ampm == "am" and hr == 12:
            hr = 0
        disp = f"{hr:02d}:{mn:02d} {ampm.upper()}" if ampm else f"{hr:02d}:{mn:02d}"
        # Standardize display (e.g. 03:00 PM)
        period = "PM" if hr >= 12 else "AM"
        disp_hr = hr if hr <= 12 else hr - 12
        disp_hr = 12 if disp_hr == 0 else disp_hr
        display_str = f"{disp_hr:02d}:{mn:02d} {period}"
        return hr, mn, display_str, t_match.group(0).strip()

    # 2. Telugu / Colloquial Time (e.g., '3 ki', '3 gantalaku', '3 gantalu', '4 ki meeting', 'repu 3 ki')
    te_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(?:ki|gantalaku|gantalu|గంటలకు|గంటలు)\b", norm, re.IGNORECASE)
    if te_match:
        hr = int(te_match.group(1))
        mn = int(te_match.group(2) or 0)
        # Infer PM if 1 <= hr <= 6 and not specified morning
        if any(m in norm for m in ["udayam", "morning", "ఉదయం"]):
            period = "AM"
            if hr == 12:
                hr = 0
        else:
            if hr < 8:
                hr += 12
            period = "PM" if hr >= 12 else "AM"
        disp_hr = hr if hr <= 12 else hr - 12
        disp_hr = 12 if disp_hr == 0 else disp_hr
        display_str = f"{disp_hr:02d}:{mn:02d} {period}"
        return hr, mn, display_str, te_match.group(0).strip()

    # 3. Relative Periods (e.g., 'morning', 'afternoon', 'evening', 'udayam', 'madhyanam', 'sayantram')
    if any(m in norm for m in ["morning", "udayam", "ఉదయం", "poddunne"]):
        return 10, 0, "10:00 AM", "morning"
    if any(m in norm for m in ["afternoon", "madhyanam", "మధ్యాహ్నం"]):
        return 14, 0, "02:00 PM", "afternoon"
    if any(m in norm for m in ["evening", "sayantram", "సాయంత్రం"]):
        return 17, 0, "05:00 PM", "evening"

    # 4. Fallback: single digit after at (e.g. 'at 3', 'at 11')
    at_match = re.search(r"\bat\s+(\d{1,2})\b", norm, re.IGNORECASE)
    if at_match:
        hr = int(at_match.group(1))
        if hr < 8:
            hr += 12
        period = "PM" if hr >= 12 else "AM"
        disp_hr = hr if hr <= 12 else hr - 12
        disp_hr = 12 if disp_hr == 0 else disp_hr
        return hr, 0, f"{disp_hr:02d}:00 {period}", at_match.group(0).strip()

    return None


def extract_reminder_preference(text: str) -> Optional[Tuple[int, str]]:
    if not text:
        return None

    norm = text.lower()
    if not any(k in norm for k in ["remind", "reminder", "gurthu", "alert", "notification"]):
        return None

    # 1. Specific minutes / hours
    if any(k in norm for k in ["30 minute", "30 min", "30 mins", "30 nimishalu", "30 నిమిషాలు"]):
        return 30, "30 minutes before"
    if any(k in norm for k in ["1 hour", "one hour", "1 hr", "an hour", "ganta mundu", "గంట ముందు"]):
        return 60, "1 hour before"
    if any(k in norm for k in ["2 hour", "two hour", "2 hr", "2 hrs", "rendu gantalu"]):
        return 120, "2 hours before"
    if any(k in norm for k in ["tomorrow morning", "repu poddunne", "morning of"]):
        return 60, "Morning of meeting"

    # Default reminder if requested generally
    return 30, "30 minutes before"


def extract_meeting_schedule_details(
    transcript: str,
    current_hcp_id: Optional[int] = None,
    current_hcp_name: Optional[str] = None,
    current_hospital: Optional[str] = None,
) -> Dict[str, Any]:
    norm = transcript.lower()

    # 1. Date parsing
    date_parsed = parse_date_expression(transcript)
    if date_parsed:
        target_date, date_display, date_ev = date_parsed
    else:
        # Default to upcoming Friday or Tomorrow if unspecified
        now = datetime.now()
        days_ahead = (4 - now.weekday() + 7) % 7
        days_ahead = 7 if days_ahead == 0 else days_ahead
        target_date = now + timedelta(days=days_ahead)
        date_display = target_date.strftime("%B %d, %Y")
        date_ev = "upcoming date"

    # 2. Time parsing
    time_parsed = parse_time_expression(transcript)
    if time_parsed:
        hr, mn, time_display, time_ev = time_parsed
    else:
        hr, mn, time_display, time_ev = 15, 0, "03:00 PM", "3:00 PM"

    meeting_datetime = target_date.replace(hour=hr, minute=mn, second=0, microsecond=0)

    # 3. Location extraction
    hosp_m = re.search(r"\b(?:at|in)\s+([A-Za-z\s]+(?:Hospital|Clinic|Care|KIMS|Apollo|Manipal|Sunshine))\b", transcript, re.IGNORECASE)
    location = hosp_m.group(1).strip() if hosp_m else (current_hospital or "Hospital Clinic")

    # 4. Reminder extraction
    reminder_pref = extract_reminder_preference(transcript)
    reminder_minutes = reminder_pref[0] if reminder_pref else 30
    reminder_display = reminder_pref[1] if reminder_pref else "30 minutes before"

    planned_actions = ["CREATE_MEETING"]
    if reminder_pref:
        planned_actions.append("CREATE_REMINDER")

    evidence = {
        "date": date_ev,
        "time": time_ev,
    }
    if reminder_pref:
        evidence["reminder"] = reminder_display

    return {
        "action_id": str(uuid.uuid4())[:8],
        "type": "SCHEDULE_MEETING",
        "meeting_time": meeting_datetime.isoformat(),
        "meeting_date_display": date_display,
        "meeting_time_display": time_display,
        "location": location,
        "reminder_minutes": reminder_minutes,
        "reminder_display": reminder_display,
        "planned_actions": planned_actions,
        "evidence": evidence,
    }


def apply_meeting_schedule_correction(
    pending_action: Dict[str, Any],
    correction_text: str,
    db_hcps: Optional[List[Any]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    updated = dict(pending_action)
    norm = correction_text.lower()
    changes = []

    # 1. Time modification (e.g. "Actually make it 4 PM", "Change it to 11 AM", "4 ki marchu")
    t_parsed = parse_time_expression(correction_text)
    if t_parsed:
        hr, mn, t_disp, _ = t_parsed
        old_dt_str = updated.get("meeting_time")
        if old_dt_str:
            try:
                cur_dt = datetime.fromisoformat(old_dt_str)
                new_dt = cur_dt.replace(hour=hr, minute=mn)
                updated["meeting_time"] = new_dt.isoformat()
            except Exception:
                pass
        updated["meeting_time_display"] = t_disp
        changes.append(f"Updated meeting time to {t_disp}")

    # 2. Date modification (e.g. "Change it to Monday", "Make it next Friday", "November 5")
    d_parsed = parse_date_expression(correction_text)
    if d_parsed:
        new_d, d_disp, _ = d_parsed
        old_dt_str = updated.get("meeting_time")
        if old_dt_str:
            try:
                cur_dt = datetime.fromisoformat(old_dt_str)
                new_dt = new_d.replace(hour=cur_dt.hour, minute=cur_dt.minute)
                updated["meeting_time"] = new_dt.isoformat()
            except Exception:
                updated["meeting_time"] = new_d.isoformat()
        updated["meeting_date_display"] = d_disp
        changes.append(f"Updated meeting date to {d_disp}")

    # 3. Reminder modification (e.g. "Remind me one hour before", "Remind me 30 minutes before")
    if any(k in norm for k in ["remind", "reminder", "gurthu", "alert"]):
        if any(k in norm for k in ["no reminder", "remove reminder", "reminder vaddu", "don't remind"]):
            updated["reminder_minutes"] = None
            updated["reminder_display"] = None
            if "CREATE_REMINDER" in updated.get("actions", []):
                updated["actions"] = [a for a in updated["actions"] if a != "CREATE_REMINDER"]
            changes.append("Removed reminder")
        else:
            rem = extract_reminder_preference(correction_text)
            if rem:
                updated["reminder_minutes"] = rem[0]
                updated["reminder_display"] = rem[1]
                if "CREATE_REMINDER" not in updated.get("actions", []):
                    updated["actions"] = updated.get("actions", []) + ["CREATE_REMINDER"]
                changes.append(f"Updated reminder to {rem[1]}")

    # 4. Doctor / HCP modification (e.g. "Actually I meant Sharma", "Change doctor to Dr Ananya")
    hcp_match = re.search(r"(?:actually\s+(?:i\s+meant|it\s+was|the\s+doctor\s+was)|doctor\s+was|doctor\s+to|change\s+doctor\s+to)\s+(?:dr\.?\s+)?([A-Za-z\s]+)", correction_text, re.IGNORECASE)
    if hcp_match:
        cand_name = hcp_match.group(1).strip()
        cand_name = re.split(r"\s+(?:not|instead|and)\b", cand_name, flags=re.IGNORECASE)[0].strip()
        if db_hcps:
            from app.ai.fuzzy_matcher import calculate_similarity
            best_hcp = None
            best_s = 0.0
            for h in db_hcps:
                s = calculate_similarity(cand_name, h.doctor_name)
                if s > best_s:
                    best_s = s
                    best_hcp = h
            if best_hcp and best_s >= 0.6:
                updated["hcp_id"] = best_hcp.id
                updated["hcp_name"] = best_hcp.doctor_name
                updated["hospital"] = best_hcp.hospital
                changes.append(f"Updated doctor to {best_hcp.doctor_name}")

    # 5. Location modification
    loc_match = re.search(r"(?:location\s+(?:is|to)|hospital\s+(?:is|to))\s+([A-Za-z\s]+(?:Hospital|Clinic|Care|KIMS|Apollo|Manipal|Sunshine))", correction_text, re.IGNORECASE)
    if loc_match:
        new_loc = loc_match.group(1).strip()
        updated["location"] = new_loc
        changes.append(f"Updated location to {new_loc}")

    return updated, changes
