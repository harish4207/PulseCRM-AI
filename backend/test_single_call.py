"""
test_single_call.py
"""
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\pulseCRM\PulseCRM-AI\backend")

from app.database.database import SessionLocal
from app.models.user import User
from app.ai.voice_copilot_graph import run_voice_copilot_graph

db = SessionLocal()
u = db.query(User).first()

try:
    res = run_voice_copilot_graph(
        db=db,
        transcript="I just met a new doctor.",
        user_id=u.id
    )
    print("SUCCESS:")
    print(res)
except Exception as e:
    print("FAILED WITH EXCEPTION:")
    traceback.print_exc()
