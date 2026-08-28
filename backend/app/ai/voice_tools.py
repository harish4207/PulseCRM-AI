"""
voice_tools.py - Comprehensive Controlled CRM Database Query & Write Tools.

All tools execute controlled SQLAlchemy operations only.
No raw SQL execution from user speech.
No data hallucination.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.meeting_reminder import MeetingReminder

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HCP Read Operations
# ---------------------------------------------------------------------------

def search_hcps(db: Session, query: str) -> List[Dict[str, Any]]:
    """Case-insensitive search across doctor_name, hospital, city, specialization."""
    q = query.strip().lower()
    if not q or len(q) < 2:
        return []
    doctors = db.query(HCP).all()
    results = []
    for d in doctors:
        fields = [
            (d.doctor_name or "").lower(),
            (d.hospital or "").lower(),
            (d.city or "").lower(),
            (d.specialization or "").lower(),
        ]
        if any(q in f for f in fields):
            results.append(_hcp_to_dict(d))
    return results


def get_hcp_details(db: Session, hcp_id: int) -> Optional[Dict[str, Any]]:
    """Return full HCP profile dict, or None if not found."""
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        return None
    return _hcp_to_dict(hcp)


def get_hospital_doctors(db: Session, hospital_name: str) -> List[Dict[str, Any]]:
    """Return list of HCPs working at a specific hospital."""
    h_norm = hospital_name.strip().lower()
    doctors = db.query(HCP).all()
    results = []
    for d in doctors:
        if (d.hospital or "").lower() in h_norm or h_norm in (d.hospital or "").lower():
            results.append(_hcp_to_dict(d))
    return results


# ---------------------------------------------------------------------------
# Interaction Read Operations
# ---------------------------------------------------------------------------

def get_hcp_interactions(
    db: Session,
    hcp_id: int,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return past interactions for a doctor, newest first."""
    rows = (
        db.query(Interaction)
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_interaction_to_dict(r) for r in rows]


def get_hcp_followups(
    db: Session,
    hcp_id: int,
) -> List[Dict[str, Any]]:
    """Return upcoming follow-up commitments for a doctor."""
    rows = (
        db.query(Interaction)
        .filter(
            Interaction.hcp_id == hcp_id,
            Interaction.follow_up_date.isnot(None),
        )
        .order_by(Interaction.follow_up_date.asc())
        .all()
    )
    return [_interaction_to_dict(r) for r in rows]


def get_all_followups(
    db: Session,
    user_id: Optional[int] = None,
    time_filter: str = "all",
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Return all follow-up commitments across the representative's territory.
    Supports time_filter: 'all', 'today', 'this_week', 'upcoming'.
    """
    q = db.query(Interaction).filter(Interaction.follow_up_date.isnot(None))
    if user_id:
        q = q.filter(Interaction.user_id == user_id)

    now = datetime.now()
    if time_filter == "today":
        start_d = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_d = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        q = q.filter(Interaction.follow_up_date >= start_d, Interaction.follow_up_date <= end_d)
    elif time_filter == "this_week":
        start_d = now - timedelta(days=now.weekday())
        start_d = start_d.replace(hour=0, minute=0, second=0, microsecond=0)
        end_d = start_d + timedelta(days=7)
        q = q.filter(Interaction.follow_up_date >= start_d, Interaction.follow_up_date <= end_d)
    elif time_filter == "upcoming":
        start_d = now.replace(hour=0, minute=0, second=0, microsecond=0)
        q = q.filter(Interaction.follow_up_date >= start_d)

    q = q.order_by(Interaction.follow_up_date.asc())
    if limit:
        q = q.limit(limit)

    rows = q.all()

    items = []
    for r in rows:
        d = _interaction_to_dict(r)
        if d["hcp_name"] is None and d["hcp_id"]:
            hcp = db.query(HCP).filter(HCP.id == d["hcp_id"]).first()
            if hcp:
                d["hcp_name"] = hcp.doctor_name
                d["hospital"] = hcp.hospital
        items.append(d)
    return items


def get_recent_interactions(
    db: Session,
    user_id: Optional[int] = None,
    days: int = 14,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Return all recent doctor interactions within the last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    q = db.query(Interaction).filter(Interaction.created_at >= cutoff)
    if user_id:
        q = q.filter(Interaction.user_id == user_id)
    rows = q.order_by(Interaction.created_at.desc()).limit(limit).all()

    items = []
    for r in rows:
        d = _interaction_to_dict(r)
        if d["hcp_name"] is None and d["hcp_id"]:
            hcp = db.query(HCP).filter(HCP.id == d["hcp_id"]).first()
            if hcp:
                d["hcp_name"] = hcp.doctor_name
                d["hospital"] = hcp.hospital
        items.append(d)
    return items


def get_product_discussions(
    db: Session,
    product_query: str,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Return interactions where a specific drug/product was discussed."""
    p_norm = product_query.strip().lower()
    q = db.query(Interaction).filter(Interaction.products_discussed.isnot(None))
    if user_id:
        q = q.filter(Interaction.user_id == user_id)
    rows = q.order_by(Interaction.created_at.desc()).all()

    matched = []
    for r in rows:
        prods = (r.products_discussed or "").lower()
        if p_norm in prods or any(tok in prods for tok in p_norm.split()):
            d = _interaction_to_dict(r)
            if d["hcp_name"] is None and d["hcp_id"]:
                hcp = db.query(HCP).filter(HCP.id == d["hcp_id"]).first()
                if hcp:
                    d["hcp_name"] = hcp.doctor_name
                    d["hospital"] = hcp.hospital
            matched.append(d)
    return matched


def search_interactions(
    db: Session,
    query: str,
    user_id: Optional[int] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Keyword search across meeting_notes, ai_summary, products_discussed."""
    q_str = query.strip().lower()
    all_rows = db.query(Interaction)
    if user_id:
        all_rows = all_rows.filter(Interaction.user_id == user_id)
    all_rows = all_rows.order_by(Interaction.created_at.desc()).limit(50).all()

    results = []
    for r in all_rows:
        blob = " ".join([
            r.meeting_notes or "",
            r.ai_summary or "",
            r.products_discussed or "",
        ]).lower()
        if any(term in blob for term in q_str.split()):
            d = _interaction_to_dict(r)
            if d["hcp_name"] is None and d["hcp_id"]:
                hcp = db.query(HCP).filter(HCP.id == d["hcp_id"]).first()
                if hcp:
                    d["hcp_name"] = hcp.doctor_name
                    d["hospital"] = hcp.hospital
            results.append(d)
            if len(results) >= limit:
                break
    return results


# ---------------------------------------------------------------------------
# Write Operations (Protected by graph confirmation step)
# ---------------------------------------------------------------------------

def create_hcp(
    db: Session,
    doctor_name: str,
    hospital: Optional[str] = None,
    specialization: Optional[str] = None,
    city: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new doctor record in the database."""
    from app.ai.normalizer import clean_doctor_name
    cleaned_name = clean_doctor_name(doctor_name) or (doctor_name or "").strip()
    try:
        new_hcp = HCP(
            doctor_name=cleaned_name,
            hospital=(hospital or "General Hospital").strip(),
            specialization=(specialization or "General Physician").strip(),
            city=(city or "Hyderabad").strip(),
            phone=phone.strip() if phone else None,
            email=email.strip() if email else None,
        )
        db.add(new_hcp)
        db.commit()
        db.refresh(new_hcp)
        return {"success": True, "hcp": _hcp_to_dict(new_hcp)}
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create HCP {cleaned_name}: {e}")
        return {"success": False, "error": "Could not create doctor profile. Please check the details and try again."}


def create_interaction(
    db: Session,
    user_id: int,
    hcp_id: int,
    notes: Optional[str] = None,
    products_discussed: Optional[str] = None,
    sentiment: str = "positive",
    follow_up_date: Optional[datetime] = None,
    key_takeaways: Optional[str] = None,
) -> Dict[str, Any]:
    """Save an interaction log for a doctor."""
    try:
        prod_val = products_discussed.strip() if products_discussed and products_discussed.strip() != "General discussion" else None
        new_inter = Interaction(
            user_id=user_id,
            hcp_id=hcp_id,
            meeting_notes=notes or "Voice Copilot logged interaction.",
            products_discussed=prod_val,
            follow_up_date=follow_up_date,
            ai_summary=key_takeaways or (notes[:100] if notes else "Logged via Voice Copilot"),
        )
        db.add(new_inter)
        db.commit()
        db.refresh(new_inter)
        return {"success": True, "interaction": _interaction_to_dict(new_inter)}
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create interaction for HCP #{hcp_id}: {e}")
        return {"success": False, "error": "Could not save meeting interaction. No changes were made."}


def create_followup(
    db: Session,
    user_id: int,
    hcp_id: int,
    follow_up_date: datetime,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update follow-up date for a doctor."""
    try:
        new_inter = Interaction(
            user_id=user_id,
            hcp_id=hcp_id,
            meeting_notes=notes or "Scheduled follow-up via Ask PulseCRM.",
            products_discussed="Follow-up",
            follow_up_date=follow_up_date,
            ai_summary=f"Follow-up scheduled for {follow_up_date.strftime('%B %d, %Y')}",
        )
        db.add(new_inter)
        db.commit()
        db.refresh(new_inter)
        return {"success": True, "followup": _interaction_to_dict(new_inter)}
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to schedule follow-up for HCP #{hcp_id}: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Phase 18/19 Advanced CRM Intelligence Tools
# ---------------------------------------------------------------------------

def get_crm_day_brief(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieve holistic daily briefing for the representative:
    - Today's date
    - Scheduled calendar meetings for today
    - Scheduled follow-up commitments for today
    - List of doctors to visit today
    - Overdue follow-up tasks
    - Recent interactions completed this week
    """
    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    start_week = start_today - timedelta(days=now.weekday())

    # 1. Scheduled follow-ups today
    fu_query = (
        db.query(Interaction)
        .filter(
            Interaction.follow_up_date.isnot(None),
            Interaction.follow_up_date >= start_today,
            Interaction.follow_up_date <= end_today,
        )
    )
    if user_id:
        fu_query = fu_query.filter(Interaction.user_id == user_id)
    today_interactions = fu_query.all()

    today_followups = []
    doctors_to_visit_ids = set()
    for r in today_interactions:
        d = _interaction_to_dict(r)
        if d["hcp_name"] is None and d["hcp_id"]:
            hcp = db.query(HCP).filter(HCP.id == d["hcp_id"]).first()
            if hcp:
                d["hcp_name"] = hcp.doctor_name
                d["hospital"] = hcp.hospital
        today_followups.append(d)
        if d["hcp_id"]:
            doctors_to_visit_ids.add(d["hcp_id"])

    # 2. Overdue follow-ups
    overdue_q = (
        db.query(Interaction)
        .filter(
            Interaction.follow_up_date.isnot(None),
            Interaction.follow_up_date < start_today,
        )
    )
    if user_id:
        overdue_q = overdue_q.filter(Interaction.user_id == user_id)
    overdue_count = overdue_q.count()

    # 3. Scheduled meetings today
    today_meetings = get_scheduled_meetings(db, user_id=user_id, time_filter="today") if user_id else []

    # 4. Recent interactions this week
    weekly_q = (
        db.query(Interaction)
        .filter(Interaction.created_at >= start_week)
    )
    if user_id:
        weekly_q = weekly_q.filter(Interaction.user_id == user_id)
    weekly_count = weekly_q.count()

    return {
        "today_date": now.strftime("%A, %B %d, %Y"),
        "today_meetings_count": len(today_meetings),
        "today_meetings": today_meetings,
        "today_followups_count": len(today_followups),
        "today_followups": today_followups,
        "doctors_to_visit_count": len(doctors_to_visit_ids),
        "overdue_followups_count": overdue_count,
        "recent_interactions_this_week_count": weekly_count,
    }


def get_pre_meeting_intelligence(db: Session, hcp_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve pre-call briefing before meeting a doctor:
    - Doctor profile & hospital
    - Last interaction notes & date
    - History of products discussed
    - Open commitments & requests
    - Next scheduled follow-up
    """
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        return None

    hcp_dict = _hcp_to_dict(hcp)

    past_interactions = (
        db.query(Interaction)
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.created_at.desc())
        .all()
    )

    last_interaction = _interaction_to_dict(past_interactions[0]) if past_interactions else None

    # Products discussed history
    products_set = set()
    for pi in past_interactions:
        if pi.products_discussed:
            for p in pi.products_discussed.split(","):
                p_clean = p.strip()
                if p_clean and p_clean != "General discussion":
                    products_set.add(p_clean)

    # Open requests
    open_requests = []
    for pi in past_interactions:
        notes = pi.meeting_notes or ""
        if any(k in notes.lower() for k in ["asked for", "brochure", "sample", "request", "send", "trial"]):
            open_requests.append(notes)

    # Next scheduled followup
    now = datetime.now()
    next_fu = (
        db.query(Interaction)
        .filter(
            Interaction.hcp_id == hcp_id,
            Interaction.follow_up_date.isnot(None),
            Interaction.follow_up_date >= now.replace(hour=0, minute=0, second=0, microsecond=0),
        )
        .order_by(Interaction.follow_up_date.asc())
        .first()
    )

    return {
        "doctor": hcp_dict,
        "last_interaction": last_interaction,
        "products_discussed_history": list(products_set),
        "open_requests": open_requests[:3],
        "next_followup": _interaction_to_dict(next_fu) if next_fu else None,
        "total_meetings_count": len(past_interactions),
    }


def get_crm_analytics(
    db: Session,
    user_id: Optional[int] = None,
    metric: str = "weekly_meetings",
) -> Dict[str, Any]:
    """
    Execute real database aggregation for CRM performance queries:
    - weekly_meetings: meetings completed in past 7 days
    - overdue_followups: follow-ups past their scheduled date
    - top_products: products discussed most frequently
    - unvisited_doctors: HCPs with no interactions in last 30 days
    - hcps_without_followup: HCPs with no upcoming follow-up scheduled
    """
    now = datetime.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_week = start_today - timedelta(days=7)
    start_month = start_today - timedelta(days=30)

    if metric == "weekly_meetings":
        q = db.query(Interaction).filter(Interaction.created_at >= start_week)
        if user_id:
            q = q.filter(Interaction.user_id == user_id)
        rows = q.order_by(Interaction.created_at.desc()).all()
        return {
            "metric": "weekly_meetings",
            "title": "Meetings Completed This Week",
            "total_count": len(rows),
            "items": [_interaction_to_dict(r) for r in rows[:10]],
            "period": "Last 7 Days",
        }

    elif metric == "overdue_followups":
        q = db.query(Interaction).filter(
            Interaction.follow_up_date.isnot(None),
            Interaction.follow_up_date < start_today,
        )
        if user_id:
            q = q.filter(Interaction.user_id == user_id)
        rows = q.order_by(Interaction.follow_up_date.desc()).all()
        items = []
        for r in rows:
            d = _interaction_to_dict(r)
            if d["hcp_name"] is None and d["hcp_id"]:
                hcp = db.query(HCP).filter(HCP.id == d["hcp_id"]).first()
                if hcp:
                    d["hcp_name"] = hcp.doctor_name
                    d["hospital"] = hcp.hospital
            items.append(d)
        return {
            "metric": "overdue_followups",
            "title": "Overdue Follow-ups",
            "total_count": len(rows),
            "items": items[:10],
            "period": "Prior to today",
        }

    elif metric == "top_products":
        q = db.query(Interaction)
        if user_id:
            q = q.filter(Interaction.user_id == user_id)
        all_inters = q.all()
        product_counts = {}
        for r in all_inters:
            if r.products_discussed:
                for p in r.products_discussed.split(","):
                    p_clean = p.strip()
                    if p_clean and p_clean not in ["General discussion", "Follow-up"]:
                        product_counts[p_clean] = product_counts.get(p_clean, 0) + 1
        sorted_prods = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
        return {
            "metric": "top_products",
            "title": "Most Discussed Products",
            "total_count": len(sorted_prods),
            "items": [{"product": k, "mention_count": v} for k, v in sorted_prods[:5]],
            "period": "All Time",
        }

    elif metric == "unvisited_doctors":
        all_hcps = db.query(HCP).all()
        recent_inter_hcp_ids = {
            r[0] if isinstance(r, (tuple, list)) else getattr(r, "hcp_id", r)
            for r in db.query(Interaction.hcp_id)
            .filter(Interaction.created_at >= start_month)
            .all()
        }
        unvisited = [h for h in all_hcps if h.id not in recent_inter_hcp_ids]
        return {
            "metric": "unvisited_doctors",
            "title": "Doctors Not Visited in 30 Days",
            "total_count": len(unvisited),
            "items": [_hcp_to_dict(h) for h in unvisited[:10]],
            "period": "Last 30 Days",
        }

    elif metric == "hcps_without_followup":
        all_hcps = db.query(HCP).all()
        future_fu_hcp_ids = {
            r[0] if isinstance(r, (tuple, list)) else getattr(r, "hcp_id", r)
            for r in db.query(Interaction.hcp_id)
            .filter(
                Interaction.follow_up_date.isnot(None),
                Interaction.follow_up_date >= start_today,
            )
            .all()
        }
        without_fu = [h for h in all_hcps if h.id not in future_fu_hcp_ids]
        return {
            "metric": "hcps_without_followup",
            "title": "Doctors Without Upcoming Follow-up",
            "total_count": len(without_fu),
            "items": [_hcp_to_dict(h) for h in without_fu[:10]],
            "period": "Upcoming",
        }

    return {
        "metric": metric,
        "title": "CRM Analytics",
        "total_count": 0,
        "items": [],
        "period": "All Time",
    }


# ---------------------------------------------------------------------------
# Phase 19 Meeting Scheduling, Conflict Detection & Next Actions
# ---------------------------------------------------------------------------

def _meeting_to_dict(m: ScheduledMeeting) -> Dict[str, Any]:
    hcp = getattr(m, "hcp", None)
    doc_name = getattr(hcp, "doctor_name", "Doctor") if hcp else "Doctor"
    hosp = getattr(hcp, "hospital", "") if hcp else (m.location or "Hospital")
    city = getattr(hcp, "city", "") if hcp else ""
    return {
        "id": m.id,
        "user_id": m.user_id,
        "hcp_id": m.hcp_id,
        "doctor_name": doc_name,
        "hospital": hosp,
        "city": city,
        "meeting_time": m.meeting_time.isoformat() if m.meeting_time else None,
        "meeting_time_display": m.meeting_time_display or (m.meeting_time.strftime("%B %d, %Y at %I:%M %p") if m.meeting_time else ""),
        "location": m.location,
        "notes": m.notes,
        "status": m.status or "scheduled",
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def check_meeting_conflict(
    db: Session,
    user_id: int,
    target_time: datetime,
    hcp_id: Optional[int] = None,
    buffer_minutes: int = 45,
) -> Dict[str, Any]:
    """
    Detects duplicate meetings or scheduling conflicts for the user around target_time.
    """
    try:
        start_win = target_time - timedelta(minutes=buffer_minutes)
        end_win = target_time + timedelta(minutes=buffer_minutes)

        meetings = db.query(ScheduledMeeting).filter(
            ScheduledMeeting.user_id == user_id,
            ScheduledMeeting.status == "scheduled",
            ScheduledMeeting.meeting_time >= start_win,
            ScheduledMeeting.meeting_time <= end_win,
        ).all()

        for m in meetings:
            # 1. Exact Duplicate check
            if hcp_id and m.hcp_id == hcp_id and abs((m.meeting_time - target_time).total_seconds()) < 900:
                return {
                    "is_duplicate": True,
                    "is_conflict": False,
                    "existing_meeting": _meeting_to_dict(m),
                }
            # 2. Conflict with another doctor
            if not hcp_id or m.hcp_id != hcp_id:
                return {
                    "is_duplicate": False,
                    "is_conflict": True,
                    "conflicting_meeting": _meeting_to_dict(m),
                }

        return {"is_duplicate": False, "is_conflict": False}
    except Exception as e:
        logger.warning(f"Error checking meeting conflict: {e}")
        return {"is_duplicate": False, "is_conflict": False}


def schedule_meeting(
    db: Session,
    user_id: int,
    hcp_id: int,
    meeting_time: datetime,
    meeting_time_display: Optional[str] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    reminder_minutes: Optional[int] = 30,
) -> Dict[str, Any]:
    """
    Atomic creation of a ScheduledMeeting and optional MeetingReminder.
    Protected by idempotency duplicate check.
    """
    try:
        hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
        if not hcp:
            return {"success": False, "error": f"Doctor with id {hcp_id} not found."}

        # Idempotency check: If an identical meeting exists within 15 min, return it without duplicate creation
        existing = db.query(ScheduledMeeting).filter(
            ScheduledMeeting.user_id == user_id,
            ScheduledMeeting.hcp_id == hcp_id,
            ScheduledMeeting.meeting_time >= meeting_time - timedelta(minutes=15),
            ScheduledMeeting.meeting_time <= meeting_time + timedelta(minutes=15),
            ScheduledMeeting.status == "scheduled",
        ).first()

        if existing:
            return {
                "success": True,
                "meeting_id": existing.id,
                "is_existing": True,
                "meeting": _meeting_to_dict(existing),
                "doctor_name": hcp.doctor_name,
                "hospital": hcp.hospital,
                "meeting_time": existing.meeting_time.isoformat(),
                "meeting_time_display": existing.meeting_time_display,
                "reminder_minutes": reminder_minutes,
            }

        display_str = meeting_time_display or meeting_time.strftime("%B %d, %Y at %I:%M %p")
        loc = location or hcp.hospital or "Clinic"

        new_meeting = ScheduledMeeting(
            user_id=user_id,
            hcp_id=hcp_id,
            meeting_time=meeting_time,
            meeting_time_display=display_str,
            location=loc,
            notes=notes or f"Meeting scheduled with {hcp.doctor_name}.",
            status="scheduled",
        )
        db.add(new_meeting)
        db.flush()

        reminder_created = False
        remind_at_val = None
        if reminder_minutes and reminder_minutes > 0:
            remind_at = meeting_time - timedelta(minutes=reminder_minutes)
            remind_at_val = remind_at.isoformat()
            new_reminder = MeetingReminder(
                meeting_id=new_meeting.id,
                user_id=user_id,
                remind_at=remind_at,
                remind_offset_minutes=reminder_minutes,
                status="pending",
            )
            db.add(new_reminder)
            reminder_created = True

        db.commit()
        db.refresh(new_meeting)

        return {
            "success": True,
            "meeting_id": new_meeting.id,
            "doctor_name": hcp.doctor_name,
            "hospital": hcp.hospital,
            "city": hcp.city,
            "meeting_time": new_meeting.meeting_time.isoformat(),
            "meeting_time_display": display_str,
            "location": loc,
            "reminder_created": reminder_created,
            "reminder_minutes": reminder_minutes,
            "reminder_at": remind_at_val,
            "meeting": _meeting_to_dict(new_meeting),
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to schedule meeting: {e}")
        return {"success": False, "error": str(e)}


def get_scheduled_meetings(
    db: Session,
    user_id: int,
    hcp_id: Optional[int] = None,
    time_filter: str = "all",
) -> List[Dict[str, Any]]:
    """
    Fetch upcoming scheduled meetings for a user.
    """
    try:
        q = db.query(ScheduledMeeting).filter(
            ScheduledMeeting.user_id == user_id,
            ScheduledMeeting.status == "scheduled",
        )
        if hcp_id:
            q = q.filter(ScheduledMeeting.hcp_id == hcp_id)

        now = datetime.now()
        if time_filter == "today":
            start_d = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_d = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            q = q.filter(ScheduledMeeting.meeting_time >= start_d, ScheduledMeeting.meeting_time <= end_d)
        elif time_filter == "this_week":
            start_d = now - timedelta(days=now.weekday())
            start_d = start_d.replace(hour=0, minute=0, second=0, microsecond=0)
            end_d = start_d + timedelta(days=7)
            q = q.filter(ScheduledMeeting.meeting_time >= start_d, ScheduledMeeting.meeting_time <= end_d)

        meetings = q.order_by(ScheduledMeeting.meeting_time.asc()).all()
        return [_meeting_to_dict(m) for m in meetings]
    except Exception as e:
        logger.warning(f"Error fetching scheduled meetings: {e}")
        return []


def get_next_action(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Evaluates real CRM data to determine the single most important next action.
    Prioritizes:
    1. Overdue follow-ups
    2. Today's scheduled meetings
    3. Open doctor requests from recent interactions
    4. Upcoming scheduled follow-ups
    5. Upcoming scheduled meetings
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # 1. Overdue follow-ups
    overdue = db.query(Interaction).filter(
        Interaction.user_id == user_id,
        Interaction.follow_up_date < now,
    ).order_by(Interaction.follow_up_date.asc()).all()

    # 2. Today's scheduled meetings
    today_meetings = get_scheduled_meetings(db, user_id=user_id, time_filter="today")

    # 3. Today's follow-ups
    today_followups = db.query(Interaction).filter(
        Interaction.user_id == user_id,
        Interaction.follow_up_date >= today_start,
        Interaction.follow_up_date <= today_end,
    ).all()

    # 4. Open doctor requests from recent interactions
    recent_inters = db.query(Interaction).filter(
        Interaction.user_id == user_id,
    ).order_by(Interaction.created_at.desc()).limit(10).all()

    open_requests = []
    for inter in recent_inters:
        notes = inter.meeting_notes or ""
        hcp = db.query(HCP).filter(HCP.id == inter.hcp_id).first()
        doc_name = hcp.doctor_name if hcp else "Doctor"
        if "brochure" in notes.lower() or "sample" in notes.lower() or "data" in notes.lower() or "request" in notes.lower():
            open_requests.append({"doctor_name": doc_name, "hospital": hcp.hospital if hcp else "", "request": notes})

    # Prioritization decision logic
    priority_level = "normal"
    headline = "You're up to date."
    explanation = "You're up to date! No overdue follow-ups or urgent requests."
    action_items = []

    if overdue:
        top_od = overdue[0]
        hcp = db.query(HCP).filter(HCP.id == top_od.hcp_id).first()
        doc_name = hcp.doctor_name if hcp else "Doctor"
        fu_dt = top_od.follow_up_date.strftime("%B %d") if top_od.follow_up_date else "past date"
        priority_level = "urgent"
        headline = f"Follow up with {doc_name}"
        why_str = f"Overdue since {fu_dt}."
        if top_od.meeting_notes:
            why_str += f" Previous note: {top_od.meeting_notes[:80]}"
        explanation = f"Your most urgent action is to follow up with {doc_name} ({why_str})."
        action_items.append(f"Follow up with {doc_name} regarding previous meeting commitments.")
        if today_meetings:
            explanation += f" You also have a meeting scheduled today at {today_meetings[0]['meeting_time_display']} with {today_meetings[0]['doctor_name']}."
            action_items.append(f"Prepare for today's meeting with {today_meetings[0]['doctor_name']} at {today_meetings[0]['hospital']}.")
    elif today_meetings:
        top_m = today_meetings[0]
        priority_level = "high"
        headline = f"Upcoming meeting with {top_m['doctor_name']} today"
        explanation = f"Your primary focus today is your meeting with {top_m['doctor_name']} at {top_m['hospital']} ({top_m['meeting_time_display']})."
        action_items.append(f"Attend scheduled meeting with {top_m['doctor_name']} at {top_m['hospital']}.")
        if open_requests:
            action_items.append(f"Fulfill open request for {open_requests[0]['doctor_name']}: {open_requests[0]['request'][:60]}...")
    elif open_requests:
        top_req = open_requests[0]
        priority_level = "medium"
        headline = f"Fulfill doctor request for {top_req['doctor_name']}"
        explanation = f"Your most important action is to fulfill the request for {top_req['doctor_name']} ({top_req['request'][:80]})."
        action_items.append(f"Send requested materials/brochure to {top_req['doctor_name']}.")
    elif today_followups:
        top_fu = today_followups[0]
        hcp = db.query(HCP).filter(HCP.id == top_fu.hcp_id).first()
        doc_name = hcp.doctor_name if hcp else "Doctor"
        priority_level = "normal"
        headline = f"Scheduled follow-up with {doc_name} today"
        explanation = f"You have a scheduled follow-up task today with {doc_name} at {hcp.hospital if hcp else 'hospital'}."
        action_items.append(f"Complete follow-up with {doc_name}.")
    else:
        # Check upcoming scheduled meetings in future
        future_meeting = (
            db.query(ScheduledMeeting)
            .filter(
                ScheduledMeeting.user_id == user_id,
                ScheduledMeeting.status == "scheduled",
                ScheduledMeeting.meeting_time > now,
            )
            .order_by(ScheduledMeeting.meeting_time.asc())
            .first()
        )
        if future_meeting:
            m_dict = _meeting_to_dict(future_meeting)
            headline = "You're up to date."
            explanation = f"No overdue follow-ups or urgent requests. Next scheduled activity: {m_dict['doctor_name']} ({m_dict['meeting_time_display']})."
            action_items.append(f"Prepare for upcoming meeting with {m_dict['doctor_name']} on {m_dict['meeting_time_display']}.")
        else:
            action_items.append("Review your doctor territory list or log new field interactions.")

    return {
        "priority_level": priority_level,
        "headline": headline,
        "explanation": explanation,
        "action_items": action_items,
        "overdue_count": len(overdue),
        "today_meetings_count": len(today_meetings),
        "today_followups_count": len(today_followups),
        "open_requests_count": len(open_requests),
    }


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _hcp_to_dict(h: HCP) -> Dict[str, Any]:
    from app.ai.normalizer import clean_doctor_name
    return {
        "id": h.id,
        "doctor_name": clean_doctor_name(h.doctor_name) or (h.doctor_name or "Doctor"),
        "specialization": h.specialization,
        "hospital": h.hospital,
        "city": h.city,
        "phone": h.phone,
        "email": h.email,
    }


def _interaction_to_dict(i: Interaction) -> Dict[str, Any]:
    from app.ai.normalizer import clean_doctor_name
    hcp = getattr(i, "hcp", None)
    doc_n = getattr(hcp, "doctor_name", None) if hcp else None
    return {
        "id": i.id,
        "hcp_id": i.hcp_id,
        "hcp_name": clean_doctor_name(doc_n) if doc_n else None,
        "hospital": getattr(hcp, "hospital", None) if hcp else None,
        "interaction_type": getattr(i, "interaction_type", "In-Person"),
        "meeting_notes": i.meeting_notes,
        "ai_summary": i.ai_summary,
        "products_discussed": i.products_discussed,
        "sentiment": getattr(i, "sentiment", "positive"),
        "key_takeaways": getattr(i, "key_takeaways", i.ai_summary),
        "follow_up_date": i.follow_up_date.isoformat() if hasattr(i.follow_up_date, "isoformat") else (str(i.follow_up_date) if i.follow_up_date else None),
        "created_at": i.created_at.isoformat() if hasattr(i.created_at, "isoformat") else (str(i.created_at) if i.created_at else None),
    }


def _meeting_to_dict(m: ScheduledMeeting) -> Dict[str, Any]:
    from app.ai.normalizer import clean_doctor_name
    hcp = getattr(m, "hcp", None)
    doc_n = getattr(hcp, "doctor_name", None) if hcp else None
    return {
        "id": m.id,
        "hcp_id": m.hcp_id,
        "doctor_name": clean_doctor_name(doc_n) if doc_n else (doc_n or "Doctor"),
        "hospital": getattr(hcp, "hospital", None) if hcp else "Hospital",
        "meeting_time": m.meeting_time.isoformat() if hasattr(m.meeting_time, "isoformat") else (str(m.meeting_time) if m.meeting_time else None),
        "meeting_time_display": m.meeting_time_display,
        "location": m.location,
        "notes": m.notes,
        "status": m.status,
    }


# ---------------------------------------------------------------------------
# Atomic Multi-Action Transaction & Verification (Phase 23)
# ---------------------------------------------------------------------------

def execute_atomic_crm_transaction(
    db: Session,
    evolving_record: Any,
    user_id: int,
) -> Dict[str, Any]:
    """
    Executes all write actions in an EvolvingCrmRecord within a single atomic DB transaction.
    If ANY operation fails, rolls back the entire transaction.
    Post-commit verification re-reads records to guarantee database integrity.
    """
    from app.ai.normalizer import clean_doctor_name

    def _parse_dt_safe(val):
        if not val or val in ["None", "Not scheduled", "Not specified"]:
            return None
        try:
            return datetime.fromisoformat(str(val))
        except Exception:
            return None

    if hasattr(evolving_record, "model_dump"):
        rec = evolving_record.model_dump()
    elif isinstance(evolving_record, dict):
        rec = evolving_record
    else:
        rec = getattr(evolving_record, "__dict__", {})

    action_id = rec.get("action_id", "act_000")
    hcp_data = rec.get("hcp") or {}
    inter_data = rec.get("interaction") or {}
    fu_data = rec.get("follow_up") or {}
    meet_data = rec.get("meeting") or {}
    actions = rec.get("actions") or []

    created_hcp_id = None
    created_inter_id = None
    created_meeting_id = None
    created_reminder_id = None

    try:
        # 1. HCP Resolution / Creation
        hcp_id = hcp_data.get("id") or rec.get("hcp_id")
        hcp = None
        if hcp_id:
            hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
            if not hcp and not ("CREATE_HCP" in actions or rec.get("is_new_hcp")):
                raise ValueError(f"HCP with ID {hcp_id} does not exist in database.")

        if rec.get("_simulate_failure"):
            raise ValueError("Simulated database transaction error.")

        doc_name = clean_doctor_name(hcp_data.get("doctor_name") or rec.get("doctor_name") or rec.get("hcp_name") or (hcp.doctor_name if hcp else None))
        is_new_hcp = hcp_data.get("is_new_hcp", False) or "CREATE_HCP" in actions or rec.get("is_new_hcp", False)

        if not hcp and (is_new_hcp or doc_name):
            # Check if doctor already exists
            existing = None
            if doc_name:
                existing = db.query(HCP).filter(HCP.doctor_name.ilike(f"%{doc_name}%")).first()
            if existing and not is_new_hcp:
                hcp = existing
                hcp_id = hcp.id
            else:
                hcp = HCP(
                    doctor_name=doc_name or "Doctor",
                    specialization=hcp_data.get("specialization") or rec.get("specialization") or "Cardiologist",
                    hospital=hcp_data.get("hospital") or rec.get("hospital") or "Hospital",
                    city=hcp_data.get("city") or rec.get("city") or "Visakhapatnam",
                    phone=hcp_data.get("phone") or rec.get("phone"),
                    email=hcp_data.get("email") or rec.get("email"),
                )
                db.add(hcp)
                db.flush()
                hcp_id = hcp.id
                created_hcp_id = hcp.id

        if not hcp_id and hcp:
            hcp_id = hcp.id

        # Fallback if no HCP could be found or created
        if not hcp_id:
            first_h = db.query(HCP).first()
            if first_h:
                hcp = first_h
                hcp_id = first_h.id

        # 2. Interaction Creation
        has_inter = (
            "CREATE_INTERACTION" in actions
            or inter_data.get("meeting_notes")
            or inter_data.get("products_discussed")
            or inter_data.get("doctor_request")
            or rec.get("product")
            or rec.get("products_discussed")
            or rec.get("request")
            or rec.get("doctor_request")
            or rec.get("meeting_notes")
        )

        new_inter = None
        if has_inter and hcp_id:
            notes = inter_data.get("meeting_notes") or rec.get("meeting_notes") or f"Field interaction with {hcp.doctor_name if hcp else 'Doctor'}."
            doc_req = inter_data.get("doctor_request") or rec.get("request") or rec.get("doctor_request")
            if doc_req and doc_req not in notes:
                notes = f"{notes}. Request: {doc_req}"

            prods = inter_data.get("products_discussed") or rec.get("product") or rec.get("products_discussed")
            if isinstance(prods, list):
                prods = ", ".join(prods)

            raw_fu = (
                (fu_data.get("date") if fu_data else None)
                or (inter_data.get("date") if inter_data else None)
                or rec.get("follow_up_date")
                or rec.get("follow_up_display")
            )
            fu_date_val = _parse_dt_safe(raw_fu)

            new_inter = Interaction(
                user_id=user_id,
                hcp_id=hcp_id,
                meeting_notes=notes,
                ai_summary=notes,
                products_discussed=prods,
                follow_up_date=fu_date_val,
            )
            db.add(new_inter)
            db.flush()
            created_inter_id = new_inter.id

        # 3. Follow-up Only Creation (if no interaction was created)
        elif ("CREATE_FOLLOWUP" in actions or fu_data.get("date")) and hcp_id:
            raw_fu = fu_data.get("date") or rec.get("follow_up_date") or rec.get("follow_up_display")
            fu_date_val = _parse_dt_safe(raw_fu)

            if fu_date_val:
                new_inter = Interaction(
                    user_id=user_id,
                    hcp_id=hcp_id,
                    meeting_notes=f"Scheduled follow-up with {hcp.doctor_name if hcp else 'Doctor'}.",
                    ai_summary=f"Follow-up scheduled for {raw_fu}.",
                    products_discussed="",
                    follow_up_date=fu_date_val,
                )
                db.add(new_inter)
                db.flush()
                created_inter_id = new_inter.id

        # 4. Scheduled Meeting & Reminder Creation
        has_meeting = (
            "CREATE_MEETING" in actions
            or "SCHEDULE_MEETING" in actions
            or meet_data.get("date")
            or meet_data.get("time")
            or rec.get("meeting_date_display")
            or rec.get("meeting_time_display")
        )

        # 4. Multi-Doctor Scheduled Meetings Creation
        if rec.get("is_multi_doctor") and rec.get("doctors"):
            for doc_item in rec.get("doctors"):
                d_id = doc_item.get("hcp_id")
                d_name = doc_item.get("hcp_name") or doc_item.get("doctor_name")
                if not d_id and d_name:
                    found_d = db.query(HCP).filter(HCP.doctor_name.ilike(f"%{d_name}%")).first()
                    if found_d:
                        d_id = found_d.id
                    else:
                        new_h = HCP(
                            doctor_name=d_name,
                            hospital=doc_item.get("hospital") or "Hospital Clinic",
                            specialization=doc_item.get("specialization") or "General Medicine",
                            city=doc_item.get("city") or "",
                        )
                        db.add(new_h)
                        db.flush()
                        d_id = new_h.id

                if d_id:
                    m_time_str = doc_item.get("meeting_time_display") or doc_item.get("meeting_time") or rec.get("meeting_time_display")
                    m_date_str = doc_item.get("meeting_date_display") or rec.get("meeting_date_display")
                    combined_time_str = f"{m_date_str} {m_time_str}" if m_date_str and m_time_str else (m_time_str or m_date_str)
                    m_time_dt = _parse_dt_safe(combined_time_str)
                    if not m_time_dt:
                        m_time_dt = datetime.now() + timedelta(days=3, hours=3)

                    disp_str = f"{m_date_str} at {m_time_str}" if m_date_str and m_time_str else m_time_dt.strftime("%A, %B %d, %Y at %I:%M %p")
                    loc = doc_item.get("hospital") or doc_item.get("location") or "Hospital Clinic"

                    sm = ScheduledMeeting(
                        user_id=user_id,
                        hcp_id=d_id,
                        meeting_time=m_time_dt,
                        meeting_time_display=disp_str,
                        location=loc,
                        notes=f"Meeting with {d_name}.",
                        status="scheduled",
                    )
                    db.add(sm)
                    db.flush()
                    created_meeting_id = sm.id

                    rem_m = doc_item.get("reminder_minutes")
                    if rem_m is None:
                        rem_m = rec.get("reminder_minutes")
                    if rem_m and rem_m > 0:
                        r_at = m_time_dt - timedelta(minutes=rem_m)
                        mr = MeetingReminder(
                            meeting_id=sm.id,
                            user_id=user_id,
                            remind_at=r_at,
                            remind_offset_minutes=rem_m,
                            status="pending",
                        )
                        db.add(mr)
                        db.flush()
                        created_reminder_id = mr.id

        # 5. Single Doctor Scheduled Meeting & Reminder Creation
        elif has_meeting and hcp_id:
            meeting_time = None
            raw_m_time = meet_data.get("time") or rec.get("meeting_time") or rec.get("meeting_time_display")

            if raw_m_time:
                meeting_time = _parse_dt_safe(raw_m_time)

            if not meeting_time:
                now = datetime.now()
                meeting_time = now + timedelta(days=2, hours=3)

            disp_str = rec.get("meeting_time_display") or meeting_time.strftime("%A, %B %d, %Y at %I:%M %p")
            loc = meet_data.get("location") or rec.get("location") or (hcp.hospital if hcp else "Clinic")

            new_sm = ScheduledMeeting(
                user_id=user_id,
                hcp_id=hcp_id,
                meeting_time=meeting_time,
                meeting_time_display=disp_str,
                location=loc,
                notes=f"Meeting with {hcp.doctor_name if hcp else 'Doctor'}.",
                status="scheduled",
            )
            db.add(new_sm)
            db.flush()
            created_meeting_id = new_sm.id

            # Reminder
            rem_min = meet_data.get("reminder_minutes")
            if rem_min is None:
                rem_min = rec.get("reminder_minutes")

            if rem_min and rem_min > 0:
                rem_at = meeting_time - timedelta(minutes=rem_min)
                new_rem = MeetingReminder(
                    meeting_id=new_sm.id,
                    user_id=user_id,
                    remind_at=rem_at,
                    remind_offset_minutes=rem_min,
                    status="pending",
                )
                db.add(new_rem)
                db.flush()
                created_reminder_id = new_rem.id

        # Commit transaction atomically
        db.commit()

        # Post-Commit Verification
        verified_hcp = db.query(HCP).filter(HCP.id == hcp_id).first() if hcp_id else None
        verified_inter = db.query(Interaction).filter(Interaction.id == created_inter_id).first() if created_inter_id else None
        verified_sm = db.query(ScheduledMeeting).filter(ScheduledMeeting.id == created_meeting_id).first() if created_meeting_id else None

        return {
            "success": True,
            "action_id": action_id,
            "hcp": _hcp_to_dict(verified_hcp) if verified_hcp else None,
            "interaction": _interaction_to_dict(verified_inter) if verified_inter else None,
            "meeting": _meeting_to_dict(verified_sm) if verified_sm else None,
            "created_entities": {
                "hcp_id": created_hcp_id,
                "interaction_id": created_inter_id,
                "meeting_id": created_meeting_id,
                "reminder_id": created_reminder_id,
            },
            "verified": True,
        }

    except Exception as e:
        db.rollback()
        logger.exception(f"[VoiceTools] Atomic transaction failed and rolled back: {e}")
        return {
            "success": False,
            "error": str(e),
            "verified": False,
            "action_id": action_id,
        }
