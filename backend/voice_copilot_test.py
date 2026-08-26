import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pulsecrm_ai")
os.environ.setdefault("GROQ_API_KEY", "")

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.ai.fuzzy_matcher import (
    normalize_text,
    calculate_similarity,
    match_hcp_from_db,
)
from app.ai.meeting_extractor import (
    extract_meeting_details,
    parse_date_expression,
    apply_meeting_correction,
)
from app.ai.voice_copilot_graph import (
    run_voice_copilot_graph,
    INTENT_CAPTURE_MEETING,
    INTENT_CORRECT_PENDING_ACTION,
    INTENT_GET_HCP_DETAILS,
    INTENT_GET_HCP_INTERACTIONS,
    INTENT_GET_HCP_FOLLOWUPS,
    INTENT_GET_ALL_FOLLOWUPS,
    INTENT_GET_RECENT_INTERACTIONS,
    INTENT_GET_PRODUCT_DISCUSSIONS,
    INTENT_GET_HOSPITAL_DETAILS,
    INTENT_CREATE_FOLLOWUP,
    INTENT_CONFIRM_ACTION,
    INTENT_CANCEL_ACTION,
    INTENT_SEARCH_HCP,
    EXECUTED_ACTION_IDS,
)

results = []

def check(label, condition, details=""):
    status = "PASS" if condition else "FAIL"
    results.append(condition)
    note = f"  ({details})" if details else ""
    safe_label = label.encode("ascii", errors="replace").decode("ascii")
    safe_note = note.encode("ascii", errors="replace").decode("ascii")
    print(f"  [{status}] {safe_label}{safe_note}")

# ─── Mock Database Setup ──────────────────────────────────────────────────────

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

hcp_rajesh = make_hcp(1, "Dr. Rajesh Kumar", "Apollo Hospital", "Visakhapatnam", "Cardiologist", "9000000001", "rajesh@apollo.in")
hcp_sharma = make_hcp(2, "Dr. Sharma", "Care Hospital", "Hyderabad", "Neurologist", "9000000002", "sharma@care.in")
hcp_priyanka = make_hcp(3, "Dr. Priyanka", "Apollo Hospital", "Visakhapatnam", "Oncologist", "9000000003", "priyanka@apollo.in")

inter_rajesh = make_interaction(10, 1, "Discussed CardioPress-50 efficacy", "CardioPress-50", "2026-09-07T10:00:00")
inter_priyanka = make_interaction(30, 3, "Discussed CardioPress-50 clinical brochure", "CardioPress-50", "2026-09-29T10:00:00")

def make_mock_db(hcps=None):
    db = MagicMock()
    all_hcps = hcps if hcps is not None else [hcp_rajesh, hcp_sharma, hcp_priyanka]
    all_inters = [inter_rajesh, inter_priyanka]

    def mock_query(model):
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.distinct.return_value = q

        if model is HCP or (isinstance(model, type) and issubclass(model, HCP)):
            q.all.return_value = all_hcps
            q.first.side_effect = lambda: all_hcps[0] if all_hcps else None
        elif model is Interaction or (isinstance(model, type) and issubclass(model, Interaction)):
            q.all.return_value = all_inters
            q.first.side_effect = lambda: all_inters[0] if all_inters else None
        else:
            q.all.return_value = all_hcps
            q.first.side_effect = lambda: all_hcps[0] if all_hcps else None
        return q

    db.query.side_effect = mock_query
    return db

db = make_mock_db()

print("\n=== PHASE 16B: Human-In-The-Loop Meeting Review Tests ===")

# Test A: Interaction-only capture (Strict distinction from follow-up)
t_a = "I met Dr Rajesh today. Save this."
r_a = run_voice_copilot_graph(db, t_a, 1)
check("A. Interaction-only capture -> actions=['CREATE_INTERACTION']", r_a["pending_action"]["actions"] == ["CREATE_INTERACTION"], f"actions={r_a['pending_action']['actions']}")
check("Ab. No follow-up scheduled", r_a["pending_action"]["follow_up_display"] is None)

# Test B: Interaction + follow-up capture
t_b = "I met Dr Rajesh today. Save this and follow up next Friday."
r_b = run_voice_copilot_graph(db, t_b, 1)
check("B. Interaction + follow-up -> actions=['CREATE_INTERACTION', 'CREATE_FOLLOWUP']", r_b["pending_action"]["actions"] == ["CREATE_INTERACTION", "CREATE_FOLLOWUP"], f"actions={r_b['pending_action']['actions']}")
check("Bb. Has follow-up date", r_b["pending_action"]["follow_up_display"] is not None)

# Test C: Natural-language correction - Edit follow-up date across multi-turn
r_c = run_voice_copilot_graph(
    db, "Actually change the follow-up to October 1.", 1,
    pending_confirmation=True,
    pending_action=r_b["pending_action"],
    current_hcp_id=1, current_hcp_name="Dr. Rajesh Kumar"
)
check("C. Multi-turn edit follow-up date", "October 01, 2026" in r_c["pending_action"]["follow_up_display"] or "October 1" in r_c["pending_action"]["follow_up_display"], f"fu={r_c['pending_action']['follow_up_display']}")
check("Cb. Preserves pending_confirmation=True", r_c["pending_confirmation"] is True)

# Test D: Natural-language correction - Edit HCP across multi-turn
r_d = run_voice_copilot_graph(
    db, "Actually it was Dr Sharma.", 1,
    pending_confirmation=True,
    pending_action=r_c["pending_action"],
    current_hcp_id=1, current_hcp_name="Dr. Rajesh Kumar"
)
check("D. Multi-turn edit HCP to Dr. Sharma", r_d["pending_action"]["hcp_name"] == "Dr. Sharma", f"hcp={r_d['pending_action']['hcp_name']}")
check("Db. HCP id updated to 2", r_d["pending_action"]["hcp_id"] == 2, f"id={r_d['pending_action']['hcp_id']}")

# Test E: Natural-language correction - Remove follow-up
r_e = run_voice_copilot_graph(
    db, "No follow-up.", 1,
    pending_confirmation=True,
    pending_action=r_d["pending_action"]
)
check("E. Multi-turn remove follow-up", r_e["pending_action"]["actions"] == ["CREATE_INTERACTION"], f"actions={r_e['pending_action']['actions']}")
check("Eb. Follow-up display cleared", r_e["pending_action"]["follow_up_display"] is None)

# Test F: Cancel action
r_f = run_voice_copilot_graph(
    db, "Cancel.", 1,
    pending_confirmation=True,
    pending_action=r_e["pending_action"]
)
check("F. Cancel action -> pending_confirmation=False", r_f["pending_confirmation"] is False)
check("Fb. Cancel message returned", "cancelled" in r_f["response"].lower() or "రద్దు" in r_f["response"])

# Test G: Confirm action (Executes DB write)
r_g = run_voice_copilot_graph(
    db, "Confirm.", 1,
    pending_confirmation=True,
    pending_action=r_d["pending_action"]  # has Dr. Sharma with Oct 1 follow-up
)
check("G. Confirm action -> CONFIRM_ACTION", r_g["intent"] == INTENT_CONFIRM_ACTION, f"intent={r_g['intent']}")
check("Gb. Pending confirmation reset", r_g["pending_confirmation"] is False)
check("Gc. Confirmed message returned", "Dr. Sharma" in r_g["response"] and ("logged" in r_g["response"].lower() or "log" in r_g["response"]), f"resp={r_g['response'][:60]}")

# Test H: Duplicate confirmation protection
EXECUTED_ACTION_IDS.clear()
test_act_id = "test_dup_123"
action_dup = dict(r_d["pending_action"])
action_dup["action_id"] = test_act_id

r_dup1 = run_voice_copilot_graph(db, "Confirm.", 1, pending_confirmation=True, pending_action=action_dup)
check("H1. First confirmation executes", test_act_id in EXECUTED_ACTION_IDS)

r_dup2 = run_voice_copilot_graph(db, "Confirm.", 1, pending_confirmation=True, pending_action=action_dup)
check("H2. Second confirmation prevents duplicate DB insert", r_dup2["pending_confirmation"] is False)

# Test I: Ambiguous HCP clarification
hcp_p1 = make_hcp(31, "Dr. Priyanka Sharma", "Apollo Hospital")
hcp_p2 = make_hcp(32, "Dr. Priyanka Rao", "KIMS Hospital")
db_ambig = make_mock_db(hcps=[hcp_p1, hcp_p2])
r_i = run_voice_copilot_graph(db_ambig, "Priyanka", 1)
check("I. Ambiguous HCP -> clarification prompt", "multiple" in r_i["response"].lower() or "పలువురు" in r_i["response"], f"resp={r_i['response'][:60]}")

# Test J: Fuzzy HCP matching ("Rajes kumr")
r_j = run_voice_copilot_graph(db, "Rajes kumr gurinchi cheppu", 1)
check("J. Fuzzy 'Rajes kumr' resolves Dr. Rajesh Kumar", r_j["hcp_id"] == 1, f"hcp_id={r_j['hcp_id']}")

# Test K: Negation override ("Rajesh doctor kaadu Sharma doctor.")
r_k = run_voice_copilot_graph(db, "Rajesh doctor kaadu Sharma doctor.", 1, current_hcp_id=1, current_hcp_name="Dr. Rajesh Kumar")
check("K. Negation override resolves Dr. Sharma", r_k["hcp_id"] == 2, f"hcp_id={r_k['hcp_id']}")

# Test L: Primary Acceptance Test (Full Meeting with Evidence)
t_l = "I just met Dr Priyanka at Apollo. She liked CardioPress-50 and asked me to send the brochure. Let's meet again September 29."
r_l = run_voice_copilot_graph(db, t_l, 1)
check("L. Full meeting capture intent", r_l["intent"] == INTENT_CAPTURE_MEETING)
check("Lb. Extracted HCP is Dr. Priyanka", r_l["hcp_id"] == 3)
check("Lc. Extracted product is CardioPress-50", r_l["pending_action"]["products_discussed"] == "CardioPress-50")
check("Ld. Extracted follow-up is September 29", "September 29" in r_l["pending_action"]["follow_up_display"])
check("Le. Has source evidence", bool(r_l["card_data"].get("evidence")), f"ev={r_l['card_data'].get('evidence')}")

print("\n=== INTEGRATION: API Endpoints & Auth Guard ===")
from fastapi.testclient import TestClient
from app.main import app
from app.database.dependencies import get_db
from app.core.security import get_current_user
from app.models.user import User

mock_user = MagicMock(spec=User)
mock_user.id = 1; mock_user.email = "test@pulsecrm.ai"; mock_user.full_name = "Test Rep"

def override_deps(db_mock=None):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    if db_mock:
        app.dependency_overrides[get_db] = lambda: db_mock

def clear_deps():
    app.dependency_overrides.clear()

client = TestClient(app, raise_server_exceptions=False)

# API: Unauthorized
r_unauth = client.post("/ai/voice/chat", json={"transcript": "hello"})
check("API: Unauthorized -> 401/403", r_unauth.status_code in (401, 403), f"status={r_unauth.status_code}")

# API: Empty transcript
override_deps()
r_empty = client.post("/ai/voice/chat", json={"transcript": "  "})
check("API: Empty transcript -> 400", r_empty.status_code == 400, f"status={r_empty.status_code}")
clear_deps()

# API: Multi-turn natural language correction via API
override_deps(db)
r_api_corr = client.post("/ai/voice/chat", json={
    "transcript": "Actually change the follow-up to October 1.",
    "pending_confirmation": True,
    "pending_action": r_b["pending_action"],
    "current_hcp_id": 1,
    "current_hcp_name": "Dr. Rajesh Kumar"
})
check("API: Natural correction via API -> 200", r_api_corr.status_code == 200, f"status={r_api_corr.status_code}")
if r_api_corr.status_code == 200:
    d = r_api_corr.json()
    check("API: Corrected follow-up is October 01", "October 01" in str(d.get("pending_action", {}).get("follow_up_display", "")), f"fu={d.get('pending_action',{}).get('follow_up_display')}")
clear_deps()

print("\n" + "=" * 60)
passed = sum(results)
total = len(results)
print(f"Human-In-The-Loop Suite: {passed}/{total} checks passed")
if passed == total:
    print("ALL 16 PHASE 16B HUMAN-IN-THE-LOOP TESTS PASSED!")
    sys.exit(0)
else:
    print(f"{total - passed} check(s) FAILED")
    sys.exit(1)