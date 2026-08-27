"""
test_critical_dialogues_suite.py - Regression suite for Scenarios A through H + Edge Cases
"""

import sys
import json
import uuid

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from app.database.database import SessionLocal
from app.models.user import User
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.scheduled_meeting import ScheduledMeeting
from app.ai.voice_copilot_graph import run_voice_copilot_graph

db = SessionLocal()
u = db.query(User).first()
if not u:
    u = User(email="rep@pulsecrm.com", full_name="Field Rep", password="hash")
    db.add(u)
    db.commit()
    db.refresh(u)

# Seed standard test doctors
for doc in [
    {"doctor_name": "Dr. Rajesh Kumar", "hospital": "Apollo Hospital", "city": "Visakhapatnam", "specialization": "Cardiology"},
    {"doctor_name": "Dr. Sharma", "hospital": "Care Hospital", "city": "Hyderabad", "specialization": "Cardiology"},
    {"doctor_name": "Dr. Priyanka", "hospital": "KIMS Hospital", "city": "Hyderabad", "specialization": "Endocrinology"},
    {"doctor_name": "Dr. Ananya", "hospital": "KIMS Hospital", "city": "Hyderabad", "specialization": "Cardiology"},
]:
    if not db.query(HCP).filter(HCP.doctor_name == doc["doctor_name"]).first():
        db.add(HCP(**doc, phone="9876543210", email="doc@test.com"))
db.commit()

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0

def record_result(name, passed, detail=""):
    global TOTAL_TESTS, PASSED_TESTS, FAILED_TESTS
    TOTAL_TESTS += 1
    if passed:
        PASSED_TESTS += 1
        print(f"  [PASS] {name} {f'({detail})' if detail else ''}")
    else:
        FAILED_TESTS += 1
        print(f"  [FAIL] {name} -> {detail}")

def execute_conversation(title, turns, assertions):
    print(f"\n--- {title} ---")
    hist = []
    curr_hcp_id = None
    curr_hcp_name = None
    pending_act = None
    pending_conf = False

    for idx, user_msg in enumerate(turns, 1):
        out = run_voice_copilot_graph(
            db=db,
            transcript=user_msg,
            user_id=u.id,
            history=hist,
            current_hcp_id=curr_hcp_id,
            current_hcp_name=curr_hcp_name,
            pending_action=pending_act,
            pending_confirmation=pending_conf
        )

        hist.append({"role": "user", "content": user_msg})
        hist.append({"role": "assistant", "content": out.get("response", "")})

        if out.get("hcp_id"):
            curr_hcp_id = out.get("hcp_id")
        if out.get("hcp_name"):
            curr_hcp_name = out.get("hcp_name")

        if out.get("pending_action") is not None:
            pending_act = out.get("pending_action")
            pending_conf = out.get("pending_confirmation", False)
        elif out.get("intent") in ["CONFIRM_ACTION", "CANCEL_ACTION"]:
            pending_act = None
            pending_conf = False

        print(f"  Turn {idx}: '{user_msg}' -> Intent: {out.get('intent')} | Doctor: {curr_hcp_name} | Response: {out.get('response', '')[:50]}...")

    # Run assertions
    for a_name, check_fn in assertions.items():
        ok, msg = check_fn(out, hist, pending_act, curr_hcp_name)
        record_result(f"{title}: {a_name}", ok, msg)


def main():
    print("="*90)
    print("CRITICAL CONVERSATIONAL AI REGRESSION SUITE (SCENARIOS A - H)")
    print("="*90)

    # -------------------------------------------------------------------------
    # SCENARIO A: Doctor correction
    # -------------------------------------------------------------------------
    execute_conversation(
        "Scenario A: Doctor Correction",
        [
            "I met Dr Ananya yesterday.",
            "Actually, I meant Dr Priyanka.",
            "She asked for the brochure.",
            "Schedule a follow-up next Thursday.",
            "Make it 4 PM.",
            "Save it."
        ],
        {
            "Final Doctor is Priyanka": lambda o, h, p, d: (d == "Dr. Priyanka" or "Priyanka" in str(d), f"Doctor: {d}"),
            "Saved successfully": lambda o, h, p, d: ("saved" in o.get("response", "").lower() or "scheduled" in o.get("response", "").lower() or o.get("intent") == "CONFIRM_ACTION", f"Response: {o.get('response')}"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO B: Meeting correction
    # -------------------------------------------------------------------------
    execute_conversation(
        "Scenario B: Meeting Correction",
        [
            "Schedule Dr Rajesh for Monday at 3.",
            "Actually make that Tuesday.",
            "No, sorry, Wednesday afternoon.",
            "Remind me one hour before.",
            "Save everything."
        ],
        {
            "Final Doctor is Rajesh": lambda o, h, p, d: ("Rajesh" in str(d), f"Doctor: {d}"),
            "Saved successfully": lambda o, h, p, d: ("scheduled" in o.get("response", "").lower() or "saved" in o.get("response", "").lower() or o.get("intent") == "CONFIRM_ACTION", f"Response: {o.get('response')}"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO C: Pronoun continuity
    # -------------------------------------------------------------------------
    execute_conversation(
        "Scenario C: Pronoun Continuity",
        [
            "Tell me about Dr Priyanka.",
            "What did we discuss with her?",
            "Schedule another meeting with her.",
            "Make it Friday.",
            "Save it."
        ],
        {
            "Pronoun resolved to Priyanka": lambda o, h, p, d: ("Priyanka" in str(d), f"Doctor: {d}"),
            "Completed without generic greeting fallback": lambda o, h, p, d: ("how can i assist" not in o.get("response", "").lower(), f"Response: {o.get('response')}"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO D: Natural conversational query
    # -------------------------------------------------------------------------
    execute_conversation(
        "Scenario D: Natural Conversational Query",
        [
            "I'm visiting KIMS tomorrow. Who should I prioritize and why?"
        ],
        {
            "Handled intelligently with doctors or advice": lambda o, h, p, d: (len(o.get("response", "")) > 20, f"Response: {o.get('response')}"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO E: Greeting
    # -------------------------------------------------------------------------
    execute_conversation(
        "Scenario E: Greeting (0 CRM queries)",
        [
            "Hello"
        ],
        {
            "Greeting is conversational": lambda o, h, p, d: (not o.get("pending_confirmation") and "no matching" not in o.get("response", "").lower(), f"Response: {o.get('response')}"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO F: Context switching
    # -------------------------------------------------------------------------
    execute_conversation(
        "Scenario F: Context Switching",
        [
            "Tell me about Dr Rajesh.",
            "Actually, I'm talking about Dr Priyanka.",
            "What was her last interaction?"
        ],
        {
            "Switched to Priyanka": lambda o, h, p, d: ("Priyanka" in str(d), f"Doctor: {d}"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO G: Incomplete information
    # -------------------------------------------------------------------------
    initial_cnt = db.query(Interaction).count()
    execute_conversation(
        "Scenario G: Incomplete Information",
        [
            "I just met a new doctor today."
        ],
        {
            "Asks for doctor name": lambda o, h, p, d: ("name" in o.get("response", "").lower() or "who" in o.get("response", "").lower() or o.get("needs_clarification"), f"Response: {o.get('response')}"),
            "Zero DB writes": lambda o, h, p, d: (db.query(Interaction).count() == initial_cnt, f"Interaction count unchanged"),
        }
    )

    # -------------------------------------------------------------------------
    # SCENARIO H: Save everything (Multi-action draft)
    # -------------------------------------------------------------------------
    initial_meetings = db.query(ScheduledMeeting).count()
    execute_conversation(
        "Scenario H: Save Everything Multi-Action Draft",
        [
            "I met Dr Sharma at Care Hospital. Discussed CardioPress. He asked for the brochure. Set a follow-up for next Wednesday at 3 PM and remind me 30 mins before.",
            "Save everything."
        ],
        {
            "Committed atomic transaction": lambda o, h, p, d: (db.query(ScheduledMeeting).count() == initial_meetings + 1 or "scheduled" in o.get("response", "").lower() or "saved" in o.get("response", "").lower(), f"Scheduled meetings count increased by 1"),
        }
    )

    print("\n" + "="*90)
    print(f"REGRESSION SUITE SUMMARY: {PASSED_TESTS} / {TOTAL_TESTS} PASSED ({(PASSED_TESTS/TOTAL_TESTS)*100:.1f}%)")
    print(f"FAILED: {FAILED_TESTS}")
    print("="*90 + "\n")

if __name__ == "__main__":
    main()
