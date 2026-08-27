"""
test_http_route.py
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
token = create_access_token({"id": u.id, "email": u.email})

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

r = requests.post("http://127.0.0.1:8003/ai/copilot/chat", headers=headers, json={"message": "I just met a new doctor."})
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
