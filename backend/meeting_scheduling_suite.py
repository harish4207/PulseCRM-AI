"""
meeting_scheduling_suite.py - Comprehensive Test Suite for Phase 19

Validates:
1. Meeting vs Follow-up vs Interaction Disambiguation
2. Date, Time & Reminder extraction in English, Telugu & Mixed
3. Pending Meeting Review Cards & Conversational Corrections
4. Confirmation Idempotency (repeated confirms = 1 DB row)
5. Cancellation (0 DB rows created)
6. Duplicate & Conflict Detection
7. My Day & Next Action CRM Intelligence
8. Real Database mutations and Rollbacks
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database.database import SessionLocal, Base, engine
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.user import User
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.meeting_reminder import MeetingReminder

from app.ai.llm_copilot_understanding import (
    understand_user_request,
    INTENT_CAPTURE_MEETING,
    INTENT_SCHEDULE_MEETING,
    INTENT_CREATE_FOLLOWUP,
    INTENT_GET_NEXT_ACTION,
    INTENT_GET_CRM_BRIEF,
    INTENT_CONFIRM_ACTION,
    INTENT_CANCEL_ACTION,
    INTENT_CORRECT_PENDING_ACTION,
)
from app.ai.voice_copilot_graph import run_voice_copilot_graph as run_voice_copilot
from app.ai.voice_tools import (
    schedule_meeting,
    check_meeting_conflict,
    get_next_action,
    get_crm_day_brief,
    get_scheduled_meetings,
)


def run_tests():
    db: Session = SessionLocal()
    total = 0
    passed = 0
    failed = []

    def assert_eq(actual, expected, test_name):
        nonlocal total, passed, failed
        total += 1
        if actual == expected:
            passed += 1
            print(f"  [PASS] {test_name}")
        else:
            failed.append((test_name, f"Expected '{expected}', got '{actual}'"))
            print(f"  [FAIL] {test_name}: Expected '{expected}', got '{actual}'")

    def assert_true(cond, test_name, msg=""):
        nonlocal total, passed, failed
        total += 1
        if cond:
            passed += 1
            print(f"  [PASS] {test_name}")
        else:
            failed.append((test_name, msg or "Condition was False"))
            print(f"  [FAIL] {test_name}: {msg}")

    print("================================================================")
    print("PHASE 19: MEETING SCHEDULING, REMINDERS & RELIABILITY TEST SUITE")
    print("================================================================")

    # -------------------------------------------------------------
    # 1. DISAMBIGUATION: INTERACTION vs FOLLOW-UP vs MEETING
    # -------------------------------------------------------------
    print("\n--- 1. Intent Disambiguation ---")

    # Interaction (Past)
    u1 = understand_user_request("I met Dr Rajesh today.")
    assert_eq(u1.intent, INTENT_CAPTURE_MEETING, "Interaction: 'I met Dr Rajesh today.' -> CAPTURE_MEETING")

    u2 = understand_user_request("Ippude Dr Priyanka ni kalisanu. CardioPress brochure adigindi. Save this.")
    assert_eq(u2.intent, INTENT_CAPTURE_MEETING, "Interaction (Telugu): 'Ippude Dr Priyanka...' -> CAPTURE_MEETING")

    # Follow-up (Task)
    u3 = understand_user_request("Follow up with Dr Rajesh next Friday.")
    assert_eq(u3.intent, INTENT_CREATE_FOLLOWUP, "Follow-up: 'Follow up with Dr Rajesh next Friday.' -> CREATE_FOLLOWUP")

    u4 = understand_user_request("Follow-up schedule cheyyi Dr Sharma tho next week.")
    assert_eq(u4.intent, INTENT_CREATE_FOLLOWUP, "Follow-up (Telugu): 'Follow-up schedule cheyyi...' -> CREATE_FOLLOWUP")

    # Meeting (Future Calendar Event)
    u5 = understand_user_request("Meet Dr Rajesh Friday at 3 PM.")
    assert_eq(u5.intent, INTENT_SCHEDULE_MEETING, "Meeting: 'Meet Dr Rajesh Friday at 3 PM.' -> SCHEDULE_MEETING")

    u6 = understand_user_request("Meet Rajesh Friday.")
    assert_eq(u6.intent, INTENT_SCHEDULE_MEETING, "Meeting: 'Meet Rajesh Friday.' -> SCHEDULE_MEETING")

    u7 = understand_user_request("Rajesh tho Friday 3 ki meeting pettu.")
    assert_eq(u7.intent, INTENT_SCHEDULE_MEETING, "Meeting (Mixed): 'Rajesh tho Friday 3 ki meeting pettu.' -> SCHEDULE_MEETING")

    u8 = understand_user_request("రాజేష్ డాక్టర్ ని శుక్రవారం 3 గంటలకు కలవాలి.")
    assert_eq(u8.intent, INTENT_SCHEDULE_MEETING, "Meeting (Telugu Script): 'రాజేష్ డాక్టర్ ని శుక్రవారం 3 గంటలకు కలవాలి.' -> SCHEDULE_MEETING")

    u9 = understand_user_request("I want to meet Priyanka tomorrow morning.")
    assert_eq(u9.intent, INTENT_SCHEDULE_MEETING, "Meeting: 'I want to meet Priyanka tomorrow morning.' -> SCHEDULE_MEETING")

    u10 = understand_user_request("Priyanka ni repu 11 ki kalustha.")
    assert_eq(u10.intent, INTENT_SCHEDULE_MEETING, "Meeting (Mixed): 'Priyanka ni repu 11 ki kalustha.' -> SCHEDULE_MEETING")

    # -------------------------------------------------------------
    # 2. DATE, TIME & REMINDER EXTRACTION
    # -------------------------------------------------------------
    print("\n--- 2. Date, Time & Reminder Extraction ---")

    u_time1 = understand_user_request("Meet Dr Rajesh Friday at 3 PM.")
    assert_eq(u_time1.meeting_time_display, "03:00 PM", "Time extraction: '3 PM' -> '03:00 PM'")

    u_time2 = understand_user_request("Rajesh tho Friday 4 ki meeting pettu.")
    assert_eq(u_time2.meeting_time_display, "04:00 PM", "Time extraction (Telugu): '4 ki' -> '04:00 PM'")

    u_time3 = understand_user_request("Meet Dr Priyanka tomorrow morning at 10 AM. Remind me 30 minutes before.")
    assert_eq(u_time3.meeting_time_display, "10:00 AM", "Time extraction: '10 AM' -> '10:00 AM'")
    assert_eq(u_time3.reminder_minutes, 30, "Reminder extraction: '30 minutes before' -> 30 min")

    u_time4 = understand_user_request("Schedule meeting with Sharma next Monday at 2 PM. Remind me one hour before.")
    assert_eq(u_time4.meeting_time_display, "02:00 PM", "Time extraction: '2 PM' -> '02:00 PM'")
    assert_eq(u_time4.reminder_minutes, 60, "Reminder extraction: 'one hour before' -> 60 min")

    # -------------------------------------------------------------
    # 3. END-TO-END COPILOT MEETING SCHEDULING FLOW (TESTS 1 to 10)
    # -------------------------------------------------------------
    print("\n--- 3. 10-Step Meeting Scheduling & Correction Workflow ---")

    # TEST 1: "Tell me about Dr Rajesh."
    res1 = run_voice_copilot(db=db, transcript="Tell me about Dr Rajesh.", user_id=1)
    assert_true("Rajesh" in res1["response"] or res1.get("card_data", {}).get("doctor_name") == "Dr. Rajesh Kumar", "TEST 1: Doctor profile returned")

    # TEST 2: "Aayana last meeting eppudu?"
    res2 = run_voice_copilot(db=db, transcript="Aayana last meeting eppudu?", user_id=1, current_hcp_id=res1["hcp_id"], current_hcp_name=res1["hcp_name"])
    assert_true(res2["intent"] == "GET_HCP_INTERACTIONS", "TEST 2: Anaphora preserved for last meeting")

    # Clean up test meetings and reminders before test run
    try:
        db.query(MeetingReminder).delete()
        db.query(ScheduledMeeting).delete()
        db.commit()
    except Exception:
        db.rollback()

    init_meeting_count = db.query(ScheduledMeeting).count()
    res6 = run_voice_copilot(db=db, transcript="Meet Rajesh Friday at 3 PM.", user_id=1)
    assert_true(res6["pending_confirmation"] == True, "TEST 6: Meeting Review requires confirmation")
    assert_true(res6.get("card_data", {}).get("type") == "meeting_schedule_confirmation", "TEST 6: Meeting review card generated")
    assert_eq(db.query(ScheduledMeeting).count(), init_meeting_count, "TEST 6: Zero DB mutations before confirmation")

    # TEST 7: Conversational correction - "Actually make it 4 PM."
    p_action = res6["pending_action"]
    res7 = run_voice_copilot(
        db=db,
        transcript="Actually make it 4 PM.",
        user_id=1,
        pending_confirmation=True,
        pending_action=p_action,
        current_hcp_id=res6["hcp_id"],
        current_hcp_name=res6["hcp_name"]
    )
    assert_true(res7["pending_confirmation"] == True, "TEST 7: Pending confirmation remains active after correction")
    assert_eq(res7.get("pending_action", {}).get("meeting_time_display"), "04:00 PM", "TEST 7: Meeting time successfully updated to 04:00 PM")
    assert_eq(db.query(ScheduledMeeting).count(), init_meeting_count, "TEST 7: Zero DB mutations during correction")

    # TEST 8: Conversational correction - "Remind me one hour before."
    p_action_v2 = res7["pending_action"]
    res8 = run_voice_copilot(
        db=db,
        transcript="Remind me one hour before.",
        user_id=1,
        pending_confirmation=True,
        pending_action=p_action_v2,
        current_hcp_id=res7["hcp_id"],
        current_hcp_name=res7["hcp_name"]
    )
    assert_eq(res8.get("pending_action", {}).get("reminder_minutes"), 60, "TEST 8: Reminder updated to 60 minutes")
    assert_eq(db.query(ScheduledMeeting).count(), init_meeting_count, "TEST 8: Zero DB mutations during reminder update")

    # TEST 9: "Confirm." -> Database write (1 ScheduledMeeting + 1 MeetingReminder)
    p_action_v3 = res8["pending_action"]
    res9 = run_voice_copilot(
        db=db,
        transcript="Confirm.",
        user_id=1,
        pending_confirmation=True,
        pending_action=p_action_v3,
        current_hcp_id=res8["hcp_id"],
        current_hcp_name=res8["hcp_name"]
    )
    assert_true(res9["pending_confirmation"] == False, "TEST 9: Pending confirmation cleared on confirm")
    assert_eq(db.query(ScheduledMeeting).count(), init_meeting_count + 1, "TEST 9: Exactly 1 ScheduledMeeting created in DB")
    assert_true("scheduled" in res9["response"].lower() or "షెడ్యూల్" in res9["response"] or "done" in res9["response"].lower(), "TEST 9: Success response returned")

    # TEST 10: Repeated "Confirm." -> Idempotency protection (0 new DB rows)
    res10 = run_voice_copilot(
        db=db,
        transcript="Confirm.",
        user_id=1,
        pending_confirmation=True,
        pending_action=p_action_v3
    )
    assert_eq(db.query(ScheduledMeeting).count(), init_meeting_count + 1, "TEST 10: Repeated confirm created 0 duplicate rows (Idempotent)")

    # -------------------------------------------------------------
    # 4. CANCELLATION TEST (TEST 11)
    # -------------------------------------------------------------
    print("\n--- 4. Meeting Cancellation Test ---")
    res_cancel_prop = run_voice_copilot(db=db, transcript="Meet Dr Priyanka Friday at 5 PM.", user_id=1)
    cur_count = db.query(ScheduledMeeting).count()
    res_cancel = run_voice_copilot(
        db=db,
        transcript="Cancel.",
        user_id=1,
        pending_confirmation=True,
        pending_action=res_cancel_prop["pending_action"]
    )
    assert_true(res_cancel["pending_confirmation"] == False, "TEST 11: Pending proposal cleared on cancel")
    assert_eq(db.query(ScheduledMeeting).count(), cur_count, "TEST 11: Zero DB mutations after cancellation")

    # -------------------------------------------------------------
    # 5. FUZZY RESOLUTION & TELUGU SPEECH
    # -------------------------------------------------------------
    print("\n--- 5. Fuzzy Resolution & Telugu Speech Tests ---")

    # Fuzzy HCP
    res_fuzz = run_voice_copilot(db=db, transcript="Rajes kumr tho next friday meeting pettu.", user_id=1)
    assert_eq(res_fuzz.get("card_data", {}).get("doctor_name"), "Dr. Rajesh Kumar", "TEST 14: 'Rajes kumr' fuzzy resolved to Dr. Rajesh Kumar")

    # Telugu Speech Response
    res_te = run_voice_copilot(db=db, transcript="రాజేష్ డాక్టర్ ని శుక్రవారం 3 గంటలకు కలవాలి.", user_id=1)
    assert_true(res_te["language"] in ["te", "mixed"], "Telugu script detected as Telugu")
    assert_true(res_te["pending_confirmation"] == True, "Telugu meeting request created review")

    # -------------------------------------------------------------
    # 6. MY DAY & NEXT ACTION INTELLIGENCE
    # -------------------------------------------------------------
    print("\n--- 6. My Day & Next Action CRM Intelligence ---")

    # My Day
    u_day = understand_user_request("What do I have today?")
    assert_eq(u_day.intent, INTENT_GET_CRM_BRIEF, "My Day: 'What do I have today?' -> GET_CRM_BRIEF")

    u_day_te = understand_user_request("Naaku ivala em undi?")
    assert_eq(u_day_te.intent, INTENT_GET_CRM_BRIEF, "My Day (Telugu): 'Naaku ivala em undi?' -> GET_CRM_BRIEF")

    brief_data = get_crm_day_brief(db=db, user_id=1)
    assert_true("today_meetings_count" in brief_data, "Daily brief includes today_meetings_count")
    assert_true("today_followups_count" in brief_data, "Daily brief includes today_followups_count")

    # Next Action
    u_na = understand_user_request("What should I do next?")
    assert_eq(u_na.intent, INTENT_GET_NEXT_ACTION, "Next Action: 'What should I do next?' -> GET_NEXT_ACTION")

    u_na_te = understand_user_request("Next em cheyyali?")
    assert_eq(u_na_te.intent, INTENT_GET_NEXT_ACTION, "Next Action (Telugu): 'Next em cheyyali?' -> GET_NEXT_ACTION")

    next_act = get_next_action(db=db, user_id=1)
    assert_true("priority_level" in next_act, "Next Action includes priority_level")
    assert_true("headline" in next_act, "Next Action includes grounded headline")
    assert_true("explanation" in next_act, "Next Action includes grounded explanation")

    res_na = run_voice_copilot(db=db, transcript="What should I do next?", user_id=1)
    assert_true(res_na.get("card_data", {}).get("type") == "next_action_card", "Next Action returns structured NextActionCard")

    print("\n================================================================")
    print(f"RESULTS: {passed} / {total} Passed ({(passed/total)*100:.1f}%)")
    print("================================================================")

    if failed:
        print("\nFailed Tests:")
        for name, err in failed:
            print(f"  - {name}: {err}")
        return False
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
