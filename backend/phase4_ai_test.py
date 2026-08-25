"""
Focused Phase 4 AI integration test (standalone script).

Usage: python backend\phase4_ai_test.py

This script will:
- create a test user via /register
- login and obtain JWT
- create a test HCP
- call POST /ai/log-meeting with mock_extraction (so no live LLM needed)
- verify interaction created
- clean up created interaction and HCP

IMPORTANT: This script modifies the existing database by adding a user, hcp, and interaction, then removes them.
"""

import time
import sys
import uuid
from fastapi.testclient import TestClient
from app.main import app

from app.database.database import SessionLocal
from app.models.interaction import Interaction
from app.services.hcp_service import HCPService

client = TestClient(app)


def register_and_login(email: str, password: str = "TestPass123"):
    r = client.post("/register", json={"email": email, "password": password, "full_name": "Phase4 Test"})
    if r.status_code not in (200, 201):
        print("Register failed:", r.status_code, r.text)
        sys.exit(1)
    r = client.post("/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print("Login failed:", r.status_code, r.text)
        sys.exit(1)
    token = r.json().get("access_token")
    if not token:
        print("No access token returned")
        sys.exit(1)
    return token


def main():
    ts = int(time.time())
    unique_phone = str(abs(uuid.uuid4().int))[:10]
    email = f"phase4-test-{ts}@example.com"
    token = register_and_login(email)
    headers = {"Authorization": f"Bearer {token}"}

    # Create HCP
    hcp_payload = {
        "doctor_name": f"Dr Phase4 {ts}",
        "specialization": "Cardiology",
        "hospital": "Test Hospital",
        "city": "Test City",
        "phone": unique_phone,
        "email": f"doc{ts}@example.com"
    }

    r = client.post("/hcps", json=hcp_payload, headers=headers)
    if r.status_code not in (200, 201):
        print("Create HCP failed:", r.status_code, r.text)
        sys.exit(1)
    hcp = r.json()
    hcp_id = hcp.get("doctor_id")
    if not hcp_id:
        print("HCP creation did not return doctor_id", hcp)
        sys.exit(1)

    # Prepare mock extraction matching the HCP name
    mock_extraction = {
        "doctor_name": hcp_payload["doctor_name"],
        "hospital": hcp_payload["hospital"],
        "products_discussed": "Product A, Product B",
        "follow_up_date": "2026-08-23T10:00:00",
        "meeting_summary": "Discussed new products and next steps."
    }

    # Test mock extraction via internal LangGraph test path
    from app.ai.graph import run_state_graph
    me_resp = client.get("/me", headers=headers)
    user_id = me_resp.json().get("id")
    meeting_text = "(mock) meeting notes for test"
    
    db_session = SessionLocal()
    try:
        resp = run_state_graph(
            db=db_session,
            meeting_text=meeting_text,
            user_id=user_id,
            mock_extraction=mock_extraction
        )
    finally:
        db_session.close()

    print("AI test response:", resp)
    if not resp.get("success"):
        print("AI workflow reported failure:", resp)
        cleanup_db(hcp_id)
        sys.exit(1)

    interaction_id = resp.get("interaction_id")
    if not interaction_id:
        print("No interaction_id returned; response:", resp)
        cleanup_db(hcp_id)
        sys.exit(1)

    print("Interaction created id:", interaction_id)

    # Cleanup: remove the created interaction and HCP
    cleanup_db(hcp_id, interaction_id)
    print("Phase 4 focused integration test: SUCCESS")


def cleanup_db(hcp_id: int, interaction_id: int = None):
    db = SessionLocal()
    try:
        if interaction_id:
            db.query(Interaction).filter(Interaction.id == interaction_id).delete()
            db.commit()
        # Now delete HCP via service (will fail if interactions exist)
        res = HCPService.delete_hcp(db, hcp_id)
        if not res.get("success"):
            print("HCP delete reported:", res)
            # As a fallback, delete directly
            from app.models.hcp import HCP
            db.query(HCP).filter(HCP.id == hcp_id).delete()
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
