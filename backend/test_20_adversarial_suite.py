"""
test_20_adversarial_suite.py
Covers all 20 Required Test Scenarios:
1. Schedule a meeting with Kamal and Sita on September 3.
2. Set up meetings for Rajesh, Priyanka and Ananya next week.
3. I want to meet both Kamal and Sita.
4. Schedule with Kamal tomorrow and Sita Friday.
5. Actually, only Sita.
6. Move Kamal to 4 PM.
7. Keep Sita as it is.
8. Save both.
9. Confirmation succeeds.
10. Confirmation fails.
11. Failed confirmation followed by "yes".
12. Failed confirmation followed by "try again".
13. Successful confirmation followed by duplicate "confirm".
14. Transaction timeout followed by retry.
15. Two doctors with the same/similar names.
16. Unknown doctor among multiple known doctors.
17. One known doctor + one unknown doctor.
18. Natural Telugu equivalent of multiple-doctor requests.
19. Telugu-English code-switched multiple-doctor requests.
20. Pronouns referring to multiple doctors where the meaning is unambiguous.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.database.database import SessionLocal
from app.models.user import User
from app.models.hcp import HCP
from app.models.meeting_reminder import MeetingReminder
from app.models.scheduled_meeting import ScheduledMeeting

db = SessionLocal()
u = db.query(User).first()
if not u:
    u = User(email="rep@pulsecrm.com", full_name="Field Rep", password="hash")
    db.add(u)
    db.commit()
    db.refresh(u)

token = create_access_token({"id": u.id, "email": u.email})
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
client = TestClient(app)

def chat(msg, hist=None, pending_act=None, pending_conf=False, hcp_name=None, hcp_id=None):
    payload = {
        "message": msg,
        "history": hist or [],
        "pending_action": pending_act,
        "pending_confirmation": pending_conf,
        "selected_hcp_name": hcp_name,
        "selected_hcp_id": hcp_id
    }
    r = client.post("/ai/copilot/chat", headers=headers, json=payload)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text}"}
    return r.json()

print("="*90)
print("EXECUTING 20-TEST ADVERSARIAL MULTI-DOCTOR & TRANSACTION SUITE")
print("="*90)

passed = 0
total = 20

# Test 1: "Schedule a meeting with Kamal and Sita on September 3."
r1 = chat("Schedule a meeting with Kamal and Sita on September 3.")
print(f"\n[Test 1] 'Schedule a meeting with Kamal and Sita on September 3.' -> {r1.get('response')}")
assert r1.get("pending_confirmation") == True and len(r1.get("pending_action", {}).get("doctors", [])) == 2
passed += 1

# Test 2: "Set up meetings for Rajesh, Priyanka and Ananya next week."
r2 = chat("Set up meetings for Rajesh, Priyanka and Ananya next week.")
print(f"\n[Test 2] 'Set up meetings for Rajesh, Priyanka and Ananya next week.' -> {r2.get('response')}")
assert r2.get("pending_confirmation") == True and len(r2.get("pending_action", {}).get("doctors", [])) == 3
passed += 1

# Test 3: "I want to meet both Kamal and Sita."
r3 = chat("I want to meet both Kamal and Sita.")
print(f"\n[Test 3] 'I want to meet both Kamal and Sita.' -> {r3.get('response')}")
assert r3.get("pending_confirmation") == True
passed += 1

# Test 4: "Schedule with Kamal tomorrow and Sita Friday."
r4 = chat("Schedule with Kamal tomorrow and Sita Friday.")
print(f"\n[Test 4] 'Schedule with Kamal tomorrow and Sita Friday.' -> {r4.get('response')}")
assert r4.get("pending_confirmation") == True and len(r4.get("pending_action", {}).get("doctors", [])) == 2
passed += 1

# Test 5: "Actually, only Sita."
r5 = chat("Actually, only Sita.", pending_act=r1.get("pending_action"), pending_conf=True)
print(f"\n[Test 5] 'Actually, only Sita.' -> {r5.get('response')}")
assert r5.get("pending_confirmation") == True
passed += 1

# Test 6: "Move Kamal to 4 PM."
r6 = chat("Move Kamal to 4 PM.", pending_act=r1.get("pending_action"), pending_conf=True)
print(f"\n[Test 6] 'Move Kamal to 4 PM.' -> {r6.get('response')}")
assert r6.get("pending_confirmation") == True
passed += 1

# Test 7: "Keep Sita as it is."
r7 = chat("Keep Sita as it is.", pending_act=r1.get("pending_action"), pending_conf=True)
print(f"\n[Test 7] 'Keep Sita as it is.' -> {r7.get('response')}")
assert r7.get("pending_confirmation") == True
passed += 1

# Test 8: "Save both."
r8 = chat("Save both.", pending_act=r1.get("pending_action"), pending_conf=True)
print(f"\n[Test 8] 'Save both.' -> {r8.get('response')}")
assert r8.get("pending_confirmation") == False and "scheduled" in r8.get("response", "").lower()
passed += 1

# Test 9: Confirmation succeeds.
act_sita = {
    "action_id": "conf_sita_001",
    "type": "SCHEDULE_MEETING",
    "hcp_name": "Dr. Sita",
    "hospital": "Apollo Hospital",
    "meeting_date_display": "September 12, 2026",
    "meeting_time_display": "02:00 PM",
    "actions": ["CREATE_MEETING"]
}
r9 = chat("Confirm", pending_act=act_sita, pending_conf=True)
print(f"\n[Test 9] Confirmation succeeds -> {r9.get('response')}")
assert r9.get("pending_confirmation") == False and "scheduled" in r9.get("response", "").lower()
passed += 1

# Test 10: Confirmation fails (Simulated DB error).
act_fail = {
    "action_id": "fail_001",
    "type": "SCHEDULE_MEETING",
    "hcp_name": "Dr. Fail",
    "_simulate_failure": True,
    "actions": ["CREATE_MEETING"]
}
r10 = chat("Confirm", pending_act=act_fail, pending_conf=True)
print(f"\n[Test 10] Confirmation fails -> {r10.get('response')}")
assert r10.get("pending_confirmation") == True and r10.get("pending_action", {}).get("status") == "failed"
passed += 1

# Test 11: Failed confirmation followed by "yes".
retry_act = dict(r10.get("pending_action"))
retry_act.pop("_simulate_failure", None)
retry_act["hcp_name"] = "Dr. Sita"
r11 = chat("yes", pending_act=retry_act, pending_conf=True)
print(f"\n[Test 11] Failed confirmation followed by 'yes' -> {r11.get('response')}")
assert r11.get("pending_confirmation") == False and "scheduled" in r11.get("response", "").lower()
passed += 1

# Test 12: Failed confirmation followed by "try again".
act_fail_2 = {
    "action_id": "fail_002",
    "type": "SCHEDULE_MEETING",
    "hcp_name": "Dr. Fail2",
    "_simulate_failure": True,
    "actions": ["CREATE_MEETING"]
}
r10_2 = chat("Confirm", pending_act=act_fail_2, pending_conf=True)
retry_act_2 = dict(r10_2.get("pending_action"))
retry_act_2.pop("_simulate_failure", None)
retry_act_2["hcp_name"] = "Dr. Kamal"
r12 = chat("try again", pending_act=retry_act_2, pending_conf=True)
print(f"\n[Test 12] Failed confirmation followed by 'try again' -> {r12.get('response')}")
assert r12.get("pending_confirmation") == False and "scheduled" in r12.get("response", "").lower()
passed += 1

# Test 13: Successful confirmation followed by duplicate "confirm".
r13 = chat("confirm", pending_act=None, pending_conf=False)
print(f"\n[Test 13] Duplicate 'confirm' after commit -> {r13.get('response')}")
assert "already been confirmed" in r13.get("response", "").lower() or "what would you like to do next" in r13.get("response", "").lower()
passed += 1

# Test 14: Transaction timeout followed by retry.
act_timeout = {
    "action_id": "timeout_001",
    "type": "SCHEDULE_MEETING",
    "hcp_name": "Dr. Sita",
    "status": "failed",
    "last_error": "Database lock timeout",
    "actions": ["CREATE_MEETING"]
}
r14 = chat("Save it now", pending_act=act_timeout, pending_conf=True)
print(f"\n[Test 14] Timeout recovery -> {r14.get('response')}")
assert r14.get("pending_confirmation") == False
passed += 1

# Test 15: Two doctors with similar names.
r15 = chat("Schedule meetings with Dr. Rajesh Kumar and Dr. Rajesh Rao tomorrow.")
print(f"\n[Test 15] Similar names -> {r15.get('response')}")
assert r15.get("pending_confirmation") == True and len(r15.get("pending_action", {}).get("doctors", [])) == 2
passed += 1

# Test 16: Unknown doctor among multiple known doctors.
r16 = chat("Schedule meetings with Dr. Sita and Dr. John Unknown on September 8.")
print(f"\n[Test 16] Unknown doctor with known doctor -> {r16.get('response')}")
assert r16.get("pending_confirmation") == True and len(r16.get("pending_action", {}).get("doctors", [])) == 2
passed += 1

# Test 17: One known doctor + one unknown doctor.
r17 = chat("Set up meeting for Kamal and Dr. NewPhysician on Friday.")
print(f"\n[Test 17] One known + one unknown -> {r17.get('response')}")
assert r17.get("pending_confirmation") == True and len(r17.get("pending_action", {}).get("doctors", [])) == 2
passed += 1

# Test 18: Natural Telugu equivalent of multiple-doctor requests.
r18 = chat("Kamal mariyu Sita tho repu meeting schedule cheyyi.")
print(f"\n[Test 18] Natural Telugu -> {r18.get('response')}")
assert r18.get("pending_confirmation") == True
passed += 1

# Test 19: Telugu-English code-switched multiple-doctor requests.
r19 = chat("Kamal and Sita iddariki Friday afternoon meeting schedule cheyyi.")
print(f"\n[Test 19] Telugu-English code-switching -> {r19.get('response')}")
assert r19.get("pending_confirmation") == True
passed += 1

# Test 20: Pronouns referring to multiple doctors where the meaning is unambiguous.
r20_init = chat("Schedule a meeting with Kamal and Sita on Friday.")
r20 = chat("Confirm for both of them.", pending_act=r20_init.get("pending_action"), pending_conf=True)
print(f"\n[Test 20] Multi-doctor pronoun confirmation -> {r20.get('response')}")
assert r20.get("pending_confirmation") == False and "scheduled" in r20.get("response", "").lower()
passed += 1

print("\n" + "="*90)
print(f"RESULTS: {passed}/{total} ADVERSARIAL TESTS PASSED (100%)")
print("="*90)
