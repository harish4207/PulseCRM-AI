"""
test_meeting_assistant_auth.py - End-to-end audit of Meeting Assistant authentication flow
"""

import sys
import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from app.core.security import create_access_token
from app.database.database import SessionLocal
from app.models.user import User

db = SessionLocal()
u = db.query(User).first()
if not u:
    u = User(email="rep@pulsecrm.com", full_name="Field Rep", password="hash")
    db.add(u)
    db.commit()
    db.refresh(u)

token = create_access_token({"id": u.id, "email": u.email})

sample_text = (
    "Met Dr Sharma at Apollo Hospital Mumbai this morning. Discussed CardioPress-50 and LipiGuard for hypertensive patients. "
    "Dr Sharma noted good efficacy with CardioPress-50 and requested a follow-up meeting on 2026-09-15 at 10 AM."
)

print("="*80)
print("TESTING MEETING ASSISTANT AUTHENTICATION FLOW")
print("="*80)

# Test 1: Authenticated request to /ai/log-meeting
print("\n1. Testing Authenticated POST /ai/log-meeting:")
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
r1 = requests.post("http://127.0.0.1:8003/ai/log-meeting", headers=headers, json={"meeting_text": sample_text})
print(f"   Status: {r1.status_code}")
print(f"   Response: {r1.text[:300]}...")
assert r1.status_code == 200, f"Expected 200 OK but got {r1.status_code}"

# Test 2: Unauthenticated request to /ai/log-meeting (Must return 401)
print("\n2. Testing Unauthenticated POST /ai/log-meeting:")
r2 = requests.post("http://127.0.0.1:8003/ai/log-meeting", json={"meeting_text": sample_text})
print(f"   Status: {r2.status_code}")
print(f"   Response: {r2.text}")
assert r2.status_code in [401, 403], f"Expected 401/403 but got {r2.status_code}"

print("\n" + "="*80)
print("MEETING ASSISTANT AUTHENTICATION AUDIT PASSED")
print("="*80)
