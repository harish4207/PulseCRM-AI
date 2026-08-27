"""
test_8_live_traces.py - Phase 24 Live Runtime Traces for 8 Key Conversational Messages

Runs the exact 8 messages sequentially and prints:
- MODEL USED
- CONVERSATION CONTEXT
- MODEL DECISION & INTENT
- TOOL SELECTED OR NO_TOOL
- TOOL RESULT
- FINAL RESPONSE
"""

import sys
import os
import json
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from app.database.database import SessionLocal
from app.models.user import User
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.ai.voice_copilot_graph import run_voice_copilot_graph

def main():
    print("="*85)
    print("PHASE 24 LIVE RUNTIME TRACES FOR 8 KEY CONVERSATIONAL MESSAGES")
    print("="*85)

    db = SessionLocal()
    u = db.query(User).first()
    user_id = u.id if u else 1

    # Ensure Dr. Rajesh and Dr. Sharma exist in DB for grounded tool tests
    rajesh = db.query(HCP).filter(HCP.doctor_name.ilike("%Rajesh%")).first()
    if not rajesh:
        rajesh = HCP(doctor_name="Dr. Rajesh Kumar", hospital="Apollo Hospital", city="Hyderabad", specialization="Cardiologist", phone="9848012345")
        db.add(rajesh)
        db.commit()
        db.refresh(rajesh)

    sharma = db.query(HCP).filter(HCP.doctor_name.ilike("%Sharma%")).first()
    if not sharma:
        sharma = HCP(doctor_name="Dr. Sharma", hospital="Care Hospital", city="Hyderabad", specialization="Neurologist", phone="9848054321")
        db.add(sharma)
        db.commit()
        db.refresh(sharma)

    sharma_inter = db.query(Interaction).filter(Interaction.hcp_id == sharma.id).first()
    if not sharma_inter:
        sharma_inter = Interaction(
            user_id=user_id,
            hcp_id=sharma.id,
            meeting_notes="Detailed discussion on NeuroCalm efficacy for neuropathy patients. Requested clinical sample packs.",
            ai_summary="Discussed NeuroCalm clinical indications and provided sample packs.",
            products_discussed="NeuroCalm",
            doctor_request="Sample packs",
        )
        db.add(sharma_inter)
        db.commit()

    test_messages = [
        "hello",
        "what can you do?",
        "I was thinking about meeting Rajesh sometime after my Hyderabad visit next week. Maybe Tuesday afternoon would work.",
        "Actually Wednesday would be better.",
        "Aayana ki reminder one hour mundu pettu.",
        "No, not Rajesh. I meant Sharma.",
        "What did we discuss with him last time?",
        "What should I do next?",
    ]

    history = []
    current_hcp_id = None
    current_hcp_name = None
    current_hospital = None
    pending_confirmation = False
    pending_action = None

    for idx, msg in enumerate(test_messages, 1):
        print(f"\n{'#'*85}")
        print(f"MESSAGE {idx}/8: \"{msg}\"")
        print(f"{'#'*85}")

        start_time = time.time()
        res = run_voice_copilot_graph(
            db=db,
            transcript=msg,
            user_id=user_id,
            history=history,
            current_hcp_id=current_hcp_id,
            current_hcp_name=current_hcp_name,
            current_hospital=current_hospital,
            pending_confirmation=pending_confirmation,
            pending_action=pending_action,
        )
        latency = time.time() - start_time

        # Update context
        if res.get("current_hcp_id") is not None:
            current_hcp_id = res.get("current_hcp_id")
        if res.get("current_hcp_name") is not None:
            current_hcp_name = res.get("current_hcp_name")
        if res.get("current_hospital") is not None:
            current_hospital = res.get("current_hospital")
        pending_confirmation = res.get("pending_confirmation", False)
        pending_action = res.get("pending_action")

        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": res.get("response", "")})

        card_data = res.get("card_data")
        tool_name = res.get("intent") if res.get("card_data") or res.get("intent") in ["GET_HCP_INTERACTIONS", "GET_ALL_FOLLOWUPS", "GET_CRM_BRIEF", "GET_NEXT_ACTION", "CONFIRM_ACTION"] else "NO_TOOL"

        print(f"  [1] CONVERSATION CONTEXT: HCP={current_hcp_name} (ID={current_hcp_id}) | PendingConf={pending_confirmation} | HistorySize={len(history)}")
        print(f"  [2] MODEL DECISION:      Intent={res.get('intent')} | Confidence={res.get('confidence', 1.0)}")
        print(f"  [3] TOOL SELECTED:       {tool_name}")
        print(f"  [4] TOOL/CARD OUTPUT:    {json.dumps(card_data, indent=2, default=str) if card_data else 'None'}")
        print(f"  [5] FINAL RESPONSE:      \"{res.get('response', '')}\"")
        print(f"  [6] EXECUTION LATENCY:   {latency:.2f} seconds")

    print("\n" + "="*85)
    print("ALL 8 LIVE RUNTIME TRACES EXECUTED SUCCESSFULLY!")
    print("="*85 + "\n")

if __name__ == "__main__":
    main()
