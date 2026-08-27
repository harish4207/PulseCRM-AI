"""
test_12turn_adversarial.py - Section 18 minimum difficult 12-turn conversation
"""

import sys
import json
import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from app.core.security import create_access_token
from app.database.database import SessionLocal
from app.models.user import User
from app.models.hcp import HCP

db = SessionLocal()
u = db.query(User).first()
token = create_access_token({"id": u.id, "email": u.email})

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

turns = [
    "I just met a new doctor.",
    "Her name is Dr Priyanka. She's a cardiologist at Apollo Hospital.",
    "We discussed CardioPress-50 and she asked for the brochure.",
    "Schedule a follow-up with her next Thursday at 3 PM.",
    "Actually make it 4 PM.",
    "Remind me one hour before.",
    "Actually don't remind me.",
    "Save everything.",
    "Confirm.",
    "What did we discuss with her?",
    "Actually, I meant Dr Rajesh.",
    "What was my last interaction with him?"
]

print("="*90)
print("SECTION 18: 12-TURN MINIMUM DIFFICULT CONVERSATIONAL TEST")
print("="*90)

hist = []
active_hcp_id = None
active_hcp_name = None
pending_act = None
pending_conf = False

for idx, user_msg in enumerate(turns, 1):
    payload = {
        "message": user_msg,
        "history": hist,
        "selected_hcp_id": active_hcp_id,
        "selected_hcp_name": active_hcp_name,
        "pending_action": pending_act,
        "pending_confirmation": pending_conf
    }

    r = requests.post("http://127.0.0.1:8003/ai/copilot/chat", headers=headers, json=payload)
    if r.status_code != 200:
        print(f"ERROR: HTTP {r.status_code}: {r.text}")
        continue
    res = r.json()

    print(f"\n[Turn {idx:02d}] User: \"{user_msg}\"")
    print(f"  -> Assistant: \"{res.get('response')}\"")
    print(f"  -> Intent: {res.get('intent')} | Active Doctor: {res.get('hcp_name')} | PendingConf: {res.get('pending_confirmation')}")

    hist.append({"role": "user", "content": user_msg})
    hist.append({"role": "assistant", "content": res.get("response", "")})

    if res.get("hcp_id"):
        active_hcp_id = res.get("hcp_id")
    if res.get("hcp_name"):
        active_hcp_name = res.get("hcp_name")

    if res.get("pending_action") is not None:
        pending_act = res.get("pending_action")
        pending_conf = res.get("pending_confirmation", False)
    elif res.get("intent") in ["CONFIRM_ACTION", "CANCEL_ACTION"]:
        pending_act = None
        pending_conf = False

print("\n" + "="*90)
print("12-TURN ADVERSARIAL TEST COMPLETED")
print("="*90)
