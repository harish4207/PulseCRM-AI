"""
debug_multi_doctor.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from app.database.database import SessionLocal
from app.models.user import User
from app.models.hcp import HCP
from app.models.meeting_reminder import MeetingReminder
from app.models.scheduled_meeting import ScheduledMeeting
from app.ai.reasoning_engine import reasoning_engine
from app.ai.voice_copilot_graph import run_voice_copilot_graph

db = SessionLocal()
u = db.query(User).first()

text = "Schedule a meeting with both Kamal and Sita on September 3."
print("1. Reasoning Result:")
r = reasoning_engine.reason(transcript=text)
print(f"   Intent: {r.intent}")
print(f"   doctor_name: {r.doctor_name}")
print(f"   doctors: {r.doctors}")
print(f"   hcp_entities: {r.hcp_entities}")

print("\n2. Graph Result:")
res = run_voice_copilot_graph(db=db, transcript=text, user_id=u.id)
print(f"   Response: {res.get('response')}")
print(f"   Pending action: {res.get('pending_action')}")
print(f"   Pending conf: {res.get('pending_confirmation')}")
