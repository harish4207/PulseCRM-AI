import sys
import os
from unittest.mock import MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pulsecrm_ai")
from app.config.settings import settings
settings.GROQ_API_KEY = ""

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.ai.voice_copilot_graph import (
    run_voice_copilot_graph,
    INTENT_GET_HCP_DETAILS,
    INTENT_SEARCH_HCP,
    INTENT_GET_HCP_INTERACTIONS,
    INTENT_GET_HCP_FOLLOWUPS,
    INTENT_GET_ALL_FOLLOWUPS,
    INTENT_GET_RECENT_INTERACTIONS,
    INTENT_GET_PRODUCT_DISCUSSIONS,
    INTENT_GET_HOSPITAL_DETAILS,
    INTENT_CAPTURE_MEETING,
    INTENT_CREATE_HCP,
    INTENT_CREATE_INTERACTION,
    INTENT_CREATE_FOLLOWUP,
    INTENT_CONFIRM_ACTION,
    INTENT_CANCEL_ACTION,
    INTENT_CORRECT_PENDING_ACTION,
    INTENT_GET_CRM_BRIEF,
    INTENT_GET_PRE_MEETING_INTELLIGENCE,
    INTENT_GET_CRM_ANALYTICS,
    INTENT_SCHEDULE_MEETING,
    INTENT_GENERAL_CRM_QUERY,
)

def make_hcp(id, name, hospital, city="Visakhapatnam", spec="Cardiologist", phone="9000000001", email="doc@hospital.in"):
    h = MagicMock(spec=HCP)
    h.id = id; h.doctor_name = name; h.hospital = hospital
    h.city = city; h.specialization = spec; h.phone = phone; h.email = email
    h.created_at = MagicMock(); h.created_at.isoformat.return_value = "2026-01-15T10:00:00"
    return h

def make_interaction(id, hcp_id, notes, products="CardioPress-50", fu="2026-09-29T10:00:00"):
    i = MagicMock(spec=Interaction)
    i.id = id; i.user_id = 1; i.hcp_id = hcp_id; i.meeting_notes = notes
    i.ai_summary = None; i.products_discussed = products
    i.__dict__["hcp"] = None
    if fu:
        fu_m = MagicMock(); fu_m.isoformat.return_value = fu
        i.follow_up_date = fu_m
    else:
        i.follow_up_date = None
    ca = MagicMock(); ca.isoformat.return_value = "2026-08-24T09:00:00"; i.created_at = ca
    return i

hcp_rajesh = make_hcp(1, "Dr. Rajesh Kumar", "Apollo Hospital", "Visakhapatnam", "Cardiologist", "9848022338", "dr.rajesh@apollo.org")
hcp_sharma = make_hcp(2, "Dr. Sharma", "Care Hospital", "Hyderabad", "Neurologist", "9848011223", "dr.sharma@care.org")
hcp_priyanka = make_hcp(3, "Dr. Priyanka", "Apollo Hospital", "Visakhapatnam", "Oncologist", "9848033449", "dr.priyanka@apollo.org")
hcp_ananya = make_hcp(4, "Dr. Ananya", "KIMS Hospital", "Hyderabad", "Endocrinologist", "9848044550", "dr.ananya@kims.org")
hcp_suresh = make_hcp(5, "Dr. Suresh Reddy", "Manipal Hospital", "Vijayawada", "Orthopedic Surgeon", "9848055661", "dr.suresh@manipal.org")

inter_rajesh = make_interaction(10, 1, "Reviewed clinical study findings for CardioPress-50.", "CardioPress-50", "2026-09-07T10:00:00")
inter_priyanka = make_interaction(30, 3, "Discussed CardioPress-50 research paper.", "CardioPress-50", "2026-09-29T10:00:00")
inter_sharma = make_interaction(40, 2, "Detailed discussion on NeuroCalm.", "NeuroCalm", None)

def make_mock_db():
    db = MagicMock()
    def query_mock(*entities, **kwargs):
        q = MagicMock()
        model = entities[0] if entities else None
        if model is HCP or getattr(model, "__name__", "") == "HCP":
            all_hcps = [hcp_rajesh, hcp_sharma, hcp_priyanka, hcp_ananya, hcp_suresh]
            q.all.return_value = all_hcps
            def filter_hcp(*args):
                fq = MagicMock()
                matched = all_hcps
                for arg in args:
                    r_val = getattr(getattr(arg, "right", None), "value", None)
                    for h in all_hcps:
                        if r_val == h.id or r_val == h.doctor_name or f"={h.id}" in str(arg):
                            matched = [h]
                            break
                fq.all.return_value = matched
                fq.first.side_effect = lambda: (matched[0] if matched else all_hcps[0])
                fq.count.return_value = len(matched)
                return fq
            q.filter.side_effect = filter_hcp
            q.first.return_value = hcp_rajesh
        elif model is Interaction or getattr(model, "__name__", "") == "Interaction":
            all_inters = [inter_rajesh, inter_priyanka, inter_sharma]
            q.all.return_value = all_inters
            q.count.return_value = len(all_inters)
            def filter_inter(*args):
                fq = MagicMock()
                matched = all_inters
                for arg in args:
                    r_val = getattr(getattr(arg, "right", None), "value", None)
                    for i in all_inters:
                        if r_val == i.hcp_id or f"={i.hcp_id}" in str(arg):
                            matched = [i]
                            break
                fq.all.return_value = matched
                fq.order_by.return_value.limit.return_value.all.return_value = matched
                fq.order_by.return_value.all.return_value = matched
                fq.first.return_value = matched[0] if matched else inter_rajesh
                fq.count.return_value = len(matched)
                return fq
            q.filter.side_effect = filter_inter
            q.order_by.return_value.limit.return_value.all.return_value = all_inters
            q.order_by.return_value.all.return_value = all_inters
            q.first.return_value = inter_rajesh
        else:
            q.all.return_value = [(1,), (2,), (3,)]
            q.distinct.return_value.all.return_value = [(1,), (2,), (3,)]
            q.filter.return_value.all.return_value = [(1,), (2,), (3,)]
            q.count.return_value = 3
        return q
    db.query.side_effect = query_mock
    return db

db = make_mock_db()

GOLDEN_CASES = [
    # 1-10: Single HCP Profile & Interaction Lookups
    {"id": 1, "t": "Dr Rajesh details cheppu", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 2, "t": "Tell me about Dr Priyanka", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Priyanka"},
    {"id": 3, "t": "Dr Sharma profile", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Sharma"},
    {"id": 4, "t": "Who is Dr Ananya?", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Ananya"},
    {"id": 5, "t": "Dr. Suresh Reddy hospital ekkada?", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Suresh Reddy"},
    {"id": 6, "t": "Rajesh tho last meeting lo em matladam?", "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 7, "t": "When did I last meet Dr Sharma?", "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Sharma"},
    {"id": 8, "t": "Priyanka next follow-up eppudu?", "expected_intent": [INTENT_GET_HCP_FOLLOWUPS], "expected_hcp": "Dr. Priyanka"},
    {"id": 9, "t": "Next follow-up date for Dr Ananya", "expected_intent": [INTENT_GET_HCP_FOLLOWUPS], "expected_hcp": "Dr. Ananya"},
    {"id": 10, "t": "Who is working as Orthopedic Surgeon in Manipal?", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP, INTENT_GET_HOSPITAL_DETAILS]},

    # 11-20: Context Memory & Pronouns (Anaphora)
    {"id": 11, "t": "Aayana last meeting eppudu?", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 12, "t": "When did I meet him last?", "ctx": {"current_hcp_id": 2, "current_hcp_name": "Dr. Sharma"}, "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Sharma"},
    {"id": 13, "t": "Aavida next follow-up eppudu?", "ctx": {"current_hcp_id": 3, "current_hcp_name": "Dr. Priyanka"}, "expected_intent": [INTENT_GET_HCP_FOLLOWUPS], "expected_hcp": "Dr. Priyanka"},
    {"id": 14, "t": "What products did I discuss with her?", "ctx": {"current_hcp_id": 4, "current_hcp_name": "Dr. Ananya"}, "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Ananya"},
    {"id": 15, "t": "Schedule a meeting with him next Monday.", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_CREATE_FOLLOWUP, INTENT_CAPTURE_MEETING, INTENT_SCHEDULE_MEETING], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 16, "t": "Aayana phone number enti?", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 17, "t": "Next follow-up date for her?", "ctx": {"current_hcp_id": 3, "current_hcp_name": "Dr. Priyanka"}, "expected_intent": [INTENT_GET_HCP_FOLLOWUPS], "expected_hcp": "Dr. Priyanka"},
    {"id": 18, "t": "When did I last see him?", "ctx": {"current_hcp_id": 5, "current_hcp_name": "Dr. Suresh Reddy"}, "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Suresh Reddy"},
    {"id": 19, "t": "Save a meeting with him today.", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 20, "t": "Aayana hospital ekkada?", "ctx": {"current_hcp_id": 2, "current_hcp_name": "Dr. Sharma"}, "expected_intent": [INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Sharma"},

    # 21-30: Territory-wide All Follow-ups
    {"id": 21, "t": "Na follow-ups anni cheppu.", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 22, "t": "What follow-ups do I have today?", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 23, "t": "Which doctors do I need to visit this week?", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 24, "t": "Today evaritho follow-up undi?", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 25, "t": "Show all my upcoming doctor meetings.", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 26, "t": "Ee vaaram schedule cheppandi.", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 27, "t": "List all scheduled followups.", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 28, "t": "Next week evarini kalavali?", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 29, "t": "Ivala nenu kalavalsina doctors evaru?", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 30, "t": "Upcoming follow ups list.", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},

    # 31-40: New HCP Creation + Multi-Action Meeting Capture
    {"id": 31, "t": "I have just met a new doctor. Her name is Dr Sheila. She was interested in Cancer Medicine. Her mobile is 94326891 and email is shalini@gmail.com. Create her in my HCP directory and save the meeting.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 32, "t": "Add a new doctor named Dr. Robert at Sunshine Hospital. Phone 9876543210. Save his details.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 33, "t": "Create new HCP Dr Meenakshi at Care Clinic and log today's meeting.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 34, "t": "Kotha doctor Dr Harika ni add cheyyi, Apollo hospital, mobile 9123456780, save this.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 35, "t": "Met new doctor Dr Vikram, phone 9988776655, email vikram@care.org. Add him to HCP list.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 36, "t": "New doctor Dr Swathi at KIMS, interested in GlycoCare, follow up next Friday, add her.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 37, "t": "Create new doctor Dr Ravi, Oncologist, Apollo Hospital. Save him.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 38, "t": "I just met a new physician Dr Deepa, mobile 9876112233. Add her and log interaction.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 39, "t": "Register new doctor Dr Venkat, Care Hospital, phone 9001122334.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 40, "t": "Add new HCP Dr Padmaja and record meeting about CardioPress-50.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},

    # 41-50: Full Natural Utterance Meeting Capture
    {"id": 41, "t": "I just met Dr Priyanka at Apollo Hospital. She was interested in CardioPress-50 and asked me to send the clinical brochure. Follow up with her on September 29. Save this.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Priyanka", "has_fu": True},
    {"id": 42, "t": "I met Dr Rajesh today. Save this.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Rajesh Kumar", "has_fu": False},
    {"id": 43, "t": "I met Dr Rajesh today. Save this and follow up next Friday.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Rajesh Kumar", "has_fu": True},
    {"id": 44, "t": "Ippude Dr Priyanka ni kalisanu. CardioPress-50 meeda interest chupinchindi. Clinical brochure pampinchamani adigindi. September 29 ki follow-up pettali. Save cheyyi.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Priyanka", "has_fu": True},
    {"id": 45, "t": "Dr Sharma tho meeting ayindi. NeuroCalm gurinchi matladam. Save this meeting.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Sharma"},
    {"id": 46, "t": "Met Dr Ananya at KIMS today. Discussed GlycoCare. Schedule follow-up for next Monday and save.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Ananya", "has_fu": True},
    {"id": 47, "t": "Logged meeting with Dr Suresh Reddy. Discussed OrthoCare. Follow up next month.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Suresh Reddy", "has_fu": True},
    {"id": 48, "t": "Dr Rajesh tho meeting finish ayindi. 10 sample packs pampali. Save this.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 49, "t": "I met Dr. Priyanka today at Apollo. She asked for sample packs. Follow up October 15. Save.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Priyanka", "has_fu": True},
    {"id": 50, "t": "Dr Sharma ni kalisanu, NeuroCalm dosage discuss chesam, save cheyyi.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Sharma"},

    # 51-60: Multi-Turn Corrections (Pending Confirmation State)
    {"id": 51, "t": "Actually change the follow-up to October 1.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 52, "t": "Actually it was Dr Sharma.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 53, "t": "No follow-up.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 54, "t": "The product was CardioPress-75, not CardioPress-50.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 55, "t": "She asked for clinical trial info, not a brochure.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 3, "hcp_name": "Dr. Priyanka", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 56, "t": "Remove the follow-up.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 3, "hcp_name": "Dr. Priyanka", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 57, "t": "Follow-up date change to November 5.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 4, "hcp_name": "Dr. Ananya", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 58, "t": "Change the doctor to Dr Ananya.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 59, "t": "There was no follow-up scheduled.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 5, "hcp_name": "Dr. Suresh Reddy", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 60, "t": "Hospital is Care, not Apollo.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 2, "hcp_name": "Dr. Sharma", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},

    # 61-70: Confirmations and Cancellations
    {"id": 61, "t": "Confirm.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c1", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 62, "t": "Avunu, save cheyyi.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c2", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 63, "t": "Yes, proceed.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c3", "type": "CAPTURE_MEETING", "hcp_id": 3, "hcp_name": "Dr. Priyanka", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 64, "t": "Cancel.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c4", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CANCEL_ACTION]},
    {"id": 65, "t": "Vaddu, cancel cheyyi.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c5", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CANCEL_ACTION]},
    {"id": 66, "t": "Okay, do it.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c6", "type": "CAPTURE_MEETING", "hcp_id": 4, "hcp_name": "Dr. Ananya", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 67, "t": "Don't save.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c7", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CANCEL_ACTION]},
    {"id": 68, "t": "Sare, save cheyyi.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c8", "type": "CAPTURE_MEETING", "hcp_id": 2, "hcp_name": "Dr. Sharma", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 69, "t": "Confirm & Save.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c9", "type": "CAPTURE_MEETING", "hcp_id": 5, "hcp_name": "Dr. Suresh Reddy", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 70, "t": "Stop, don't do it.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "c10", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CANCEL_ACTION]},

    # 71-80: Fuzzy Matching & Speech Errors
    {"id": 71, "t": "Rajes kumr gurinchi cheppu", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 72, "t": "Dr. Shama at Care Hospital", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Sharma"},
    {"id": 73, "t": "Priynka docter details", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Priyanka"},
    {"id": 74, "t": "Ananya docter", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Ananya"},
    {"id": 75, "t": "Suresh redy gurinchi", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Suresh Reddy"},
    {"id": 76, "t": "Rajes kumar tho last meeting eppudu", "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 77, "t": "Dr. Priyankaa next follow app", "expected_intent": [INTENT_GET_HCP_FOLLOWUPS], "expected_hcp": "Dr. Priyanka"},
    {"id": 78, "t": "Anania doctor profile", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Ananya"},
    {"id": 79, "t": "Dr. Rajsh Kumar details", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 80, "t": "Sharmma doctor", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Sharma"},

    # 81-90: Product Questions across doctors
    {"id": 81, "t": "CardioPress-50 gurinchi evaritho matladam?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 82, "t": "Who did I discuss NeuroCalm with?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 83, "t": "GlycoCare meeda ఏ doctors tho meeting ayindi?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 84, "t": "Which doctor was interested in CardioPress-50?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 85, "t": "NeuroCalm discussion records.", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 86, "t": "Who did I present GlycoCare to?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 87, "t": "CardioPress-75 gurinchi evaritho discuss chesam?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 88, "t": "Cancer Medicine meeda interested doctor evaru?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 89, "t": "Which physicians discussed CardioPress-50?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 90, "t": "NeuroCalm patients adherence evaritho discuss ayindi?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},

    # 91-100: Hospitals, Context Overrides, Recent interactions
    {"id": 91, "t": "Apollo Hospital lo unna doctors list cheppu.", "expected_intent": [INTENT_GET_HOSPITAL_DETAILS]},
    {"id": 92, "t": "Who are the doctors at Care Hospital?", "expected_intent": [INTENT_GET_HOSPITAL_DETAILS]},
    {"id": 93, "t": "KIMS Hospital doctors list.", "expected_intent": [INTENT_GET_HOSPITAL_DETAILS]},
    {"id": 94, "t": "Manipal Hospital lo evaru unnaru?", "expected_intent": [INTENT_GET_HOSPITAL_DETAILS]},
    {"id": 95, "t": "Rajesh kaadu Sharma doctor.", "expected_intent": [INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Sharma"},
    {"id": 96, "t": "Priyanka kaadu Ananya doctor gurinchi cheppu.", "expected_intent": [INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Ananya"},
    {"id": 97, "t": "Not Rajesh, I meant Dr Sharma.", "expected_intent": [INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Sharma"},
    {"id": 98, "t": "Recent ga evarini kalisanu?", "expected_intent": [INTENT_GET_RECENT_INTERACTIONS]},
    {"id": 99, "t": "Who did I meet recently?", "expected_intent": [INTENT_GET_RECENT_INTERACTIONS]},
    {"id": 100, "t": "Show my recent interactions.", "expected_intent": [INTENT_GET_RECENT_INTERACTIONS]},

    # 101-105: Short lookups
    {"id": 101, "t": "Priyanka", "expected_intent": [INTENT_SEARCH_HCP, INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Priyanka"},
    {"id": 102, "t": "Sharma", "expected_intent": [INTENT_SEARCH_HCP, INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Sharma"},
    {"id": 103, "t": "Dr. Rajesh", "expected_intent": [INTENT_SEARCH_HCP, INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 104, "t": "Ananya", "expected_intent": [INTENT_SEARCH_HCP, INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Ananya"},
    {"id": 105, "t": "Suresh Reddy", "expected_intent": [INTENT_SEARCH_HCP, INTENT_GET_HCP_DETAILS], "expected_hcp": "Dr. Suresh Reddy"},

    # =========================================================================
    # PHASE 18 NEW SCENARIOS (106 - 160)
    # =========================================================================

    # 106-115: CRM Brief Scenarios ("Give me my day", "Today summary", etc.)
    {"id": 106, "t": "Give me my day", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 107, "t": "Today briefing", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 108, "t": "Give me today's brief", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 109, "t": "Ee roju schedule brief cheyyi", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 110, "t": "Daily brief", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 111, "t": "What does my day look like?", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 112, "t": "Today summary", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 113, "t": "Ee roju summary cheppu", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 114, "t": "CRM brief", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 115, "t": "Morning brief", "expected_intent": [INTENT_GET_CRM_BRIEF]},

    # 116-125: Pre-Meeting Intelligence Scenarios
    {"id": 116, "t": "I'm meeting Dr Rajesh today. What should I know?", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 117, "t": "What should I know before meeting Dr Priyanka?", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Priyanka"},
    {"id": 118, "t": "Brief me on Dr Sharma before meeting", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Sharma"},
    {"id": 119, "t": "Dr Ananya meeting briefing", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Ananya"},
    {"id": 120, "t": "Rajesh doctor ni kalavabothunna, details cheppu", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 121, "t": "Pre-meeting prep for Dr Suresh Reddy", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Suresh Reddy"},
    {"id": 122, "t": "What should I know about him before meeting?", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 123, "t": "Info before meeting with Dr Sharma", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Sharma"},
    {"id": 124, "t": "Meeting Dr Priyanka today. What should I know?", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Priyanka"},
    {"id": 125, "t": "Dr Ananya tho meeting mundu details cheppu", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Ananya"},

    # 126-140: CRM Analytics Scenarios
    {"id": 126, "t": "How many doctors did I meet this week?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 127, "t": "Which products did I discuss most?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 128, "t": "How many follow-ups are overdue?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 129, "t": "Which doctors haven't I visited recently?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 130, "t": "Which HCPs have no upcoming follow-up?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 131, "t": "How many meetings completed this week?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 132, "t": "Overdue follow-ups list", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 133, "t": "Most discussed products", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 134, "t": "Unvisited doctors in last 30 days", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 135, "t": "How many followups are overdue?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 136, "t": "Top products discussed", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 137, "t": "Doctors I haven't visited in 30 days", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 138, "t": "Doctors with no upcoming follow up", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 139, "t": "Weekly meetings count", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 140, "t": "How many doctors did I visit this week?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},

    # 141-160: Multimodal Text + Voice Cross-Turn Conversations
    {"id": 141, "t": "Tell me about Dr Rajesh", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 142, "t": "Aayana last meeting eppudu?", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 143, "t": "What products did we discuss with him?", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_GET_HCP_INTERACTIONS], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 144, "t": "Create a follow-up for next Friday.", "ctx": {"current_hcp_id": 1, "current_hcp_name": "Dr. Rajesh Kumar"}, "expected_intent": [INTENT_CREATE_FOLLOWUP, INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Rajesh Kumar"},
    {"id": 145, "t": "Actually make that Monday.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 146, "t": "Avunu, save cheyyi.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "m146", "type": "CAPTURE_MEETING", "hcp_id": 1, "hcp_name": "Dr. Rajesh Kumar", "actions": ["CREATE_INTERACTION", "CREATE_FOLLOWUP"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 147, "t": "I met Dr Suresh Reddy today. Save this.", "expected_intent": [INTENT_CAPTURE_MEETING], "expected_hcp": "Dr. Suresh Reddy"},
    {"id": 148, "t": "Actually it was Dr Sharma.", "ctx": {"pending_confirmation": True, "pending_action": {"type": "CAPTURE_MEETING", "hcp_id": 5, "hcp_name": "Dr. Suresh Reddy", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CORRECT_PENDING_ACTION]},
    {"id": 149, "t": "Cancel.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "m149", "type": "CAPTURE_MEETING", "hcp_id": 2, "hcp_name": "Dr. Sharma", "actions": ["CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CANCEL_ACTION]},
    {"id": 150, "t": "Give me my day", "expected_intent": [INTENT_GET_CRM_BRIEF]},
    {"id": 151, "t": "What should I know before meeting Dr Priyanka?", "expected_intent": [INTENT_GET_PRE_MEETING_INTELLIGENCE], "expected_hcp": "Dr. Priyanka"},
    {"id": 152, "t": "How many meetings completed this week?", "expected_intent": [INTENT_GET_CRM_ANALYTICS]},
    {"id": 153, "t": "Apollo Hospital lo unna doctors list cheppu.", "expected_intent": [INTENT_GET_HOSPITAL_DETAILS]},
    {"id": 154, "t": "Na follow-ups anni cheppu.", "expected_intent": [INTENT_GET_ALL_FOLLOWUPS]},
    {"id": 155, "t": "I have just met a new doctor Dr Sheila. Save this.", "expected_intent": [INTENT_CAPTURE_MEETING, INTENT_CREATE_HCP], "is_new_hcp": True},
    {"id": 156, "t": "Confirm.", "ctx": {"pending_confirmation": True, "pending_action": {"action_id": "m156", "type": "CAPTURE_MEETING", "hcp_name": "Dr. Sheila", "actions": ["CREATE_HCP", "CREATE_INTERACTION"]}}, "expected_intent": [INTENT_CONFIRM_ACTION]},
    {"id": 157, "t": "Who did I discuss NeuroCalm with?", "expected_intent": [INTENT_GET_PRODUCT_DISCUSSIONS]},
    {"id": 158, "t": "Dr Sharma profile details", "expected_intent": [INTENT_GET_HCP_DETAILS, INTENT_SEARCH_HCP], "expected_hcp": "Dr. Sharma"},
    {"id": 159, "t": "Next follow-up date for her?", "ctx": {"current_hcp_id": 4, "current_hcp_name": "Dr. Ananya"}, "expected_intent": [INTENT_GET_HCP_FOLLOWUPS], "expected_hcp": "Dr. Ananya"},
    {"id": 160, "t": "Recent ga evarini kalisanu?", "expected_intent": [INTENT_GET_RECENT_INTERACTIONS]},
]

if __name__ == "__main__":
    print(f"\n=== RUNNING {len(GOLDEN_CASES)} GOLDEN CONVERSATION TESTS (PHASE 18) ===")
    passed = 0
    failed = 0

    for case in GOLDEN_CASES:
        c_id = case["id"]
        t = case["t"]
        ctx = case.get("ctx", {})
        r = run_voice_copilot_graph(
            db,
            t,
            user_id=1,
            current_hcp_id=ctx.get("current_hcp_id"),
            current_hcp_name=ctx.get("current_hcp_name"),
            pending_confirmation=ctx.get("pending_confirmation", False),
            pending_action=ctx.get("pending_action"),
        )

        intent_ok = r["intent"] in case["expected_intent"]
        hcp_ok = True
        if "expected_hcp" in case:
            hcp_ok = (r.get("hcp_name") == case["expected_hcp"]) or (case["expected_hcp"] in (r.get("response") or ""))
        if case.get("is_new_hcp"):
            hcp_ok = bool(r.get("pending_action", {}).get("is_new_hcp") if r.get("pending_action") else False)
        if "has_fu" in case:
            act_has_fu = "CREATE_FOLLOWUP" in r.get("pending_action", {}).get("actions", []) if r.get("pending_action") else False
            hcp_ok = hcp_ok and (act_has_fu == case["has_fu"])

        is_pass = intent_ok and hcp_ok
        if is_pass:
            passed += 1
            safe_t = t.encode("ascii", errors="replace").decode("ascii")
            print(f"  [PASS] #{c_id:03d}: '{safe_t}' -> Intent: {r['intent']}")
        else:
            failed += 1
            safe_t = t.encode("ascii", errors="replace").decode("ascii")
            print(f"  [FAIL] #{c_id:03d}: '{safe_t}' -> Got Intent: {r['intent']}, HCP: {r.get('hcp_name')} (Expected Intent: {case['expected_intent']})")

    print("\n" + "=" * 60)
    print(f"Golden Suite Results: {passed}/{len(GOLDEN_CASES)} passed ({failed} failed)")
    if passed == len(GOLDEN_CASES):
        print(f"ALL {len(GOLDEN_CASES)} GOLDEN CONVERSATION TESTS PASSED PERFECTLY!")
        sys.exit(0)
    else:
        print(f"FAILED: {failed} test(s) did not match expectations.")
        sys.exit(1)
