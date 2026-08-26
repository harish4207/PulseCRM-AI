"""
Phase 20 Comprehensive Reliability Test Suite
Covers:
- Title Normalization (no 'Dr. Dr', 'Doctor Dr', trailing 'new')
- Elimination of Invented Products (no 'General discussion')
- Elimination of Raw Internal Extraction Output Leakage
- Strict Invariant Separation (Interaction vs Follow-up vs Meeting vs Reminder)
- Entity Resolution & Safe New HCP Registration
- Multi-Turn Conversation Memory & Anaphora
- Context Override & Ambiguity Resolution
- Correction on Pending Meeting
- My Day & Next Action Integration
"""

import sys
import os
import unittest
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.normalizer import clean_doctor_name, normalize_transcript
from app.ai.llm_copilot_understanding import understand_user_request
from app.ai.voice_copilot_graph import (
    run_voice_copilot_graph,
    VoiceCopilotState,
    INTENT_GET_HCP_DETAILS,
    INTENT_CAPTURE_MEETING,
    INTENT_SCHEDULE_MEETING,
    INTENT_CREATE_FOLLOWUP,
    INTENT_CONFIRM_ACTION,
    INTENT_CANCEL_ACTION,
    INTENT_CORRECT_PENDING_ACTION,
    INTENT_GET_CRM_BRIEF,
    INTENT_GET_NEXT_ACTION,
)
from app.database.database import SessionLocal, engine, Base
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.meeting_reminder import MeetingReminder
from app.models.user import User


class TestPhase20Reliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.user_id = 1

        # Clean old test data
        try:
            cls.db.query(MeetingReminder).delete()
            cls.db.query(ScheduledMeeting).delete()
            cls.db.commit()
        except Exception:
            cls.db.rollback()

        # Seed doctors
        doc_rajesh = cls.db.query(HCP).filter(HCP.doctor_name == "Dr. Rajesh Kumar").first()
        if not doc_rajesh:
            doc_rajesh = HCP(
                doctor_name="Dr. Rajesh Kumar",
                specialization="Cardiology",
                hospital="Apollo Hospitals",
                city="Hyderabad",
                phone="9876543210",
                email="rajesh@apollo.com",
            )
            cls.db.add(doc_rajesh)

        doc_priyanka = cls.db.query(HCP).filter(HCP.doctor_name == "Dr. Priyanka Sharma").first()
        if not doc_priyanka:
            doc_priyanka = HCP(
                doctor_name="Dr. Priyanka Sharma",
                specialization="Endocrinology",
                hospital="Care Hospitals",
                city="Hyderabad",
                phone="9876543211",
                email="priyanka@care.com",
            )
            cls.db.add(doc_priyanka)

        doc_sharma = cls.db.query(HCP).filter(HCP.doctor_name == "Dr. Sharma").first()
        if not doc_sharma:
            doc_sharma = HCP(
                doctor_name="Dr. Sharma",
                specialization="Neurology",
                hospital="Yashoda Hospitals",
                city="Hyderabad",
                phone="9876543212",
                email="sharma@yashoda.com",
            )
            cls.db.add(doc_sharma)

        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # =========================================================================
    # PART 1: Title Normalization Tests (Bug 2)
    # =========================================================================
    def test_title_normalization_variations(self):
        self.assertEqual(clean_doctor_name("Dr Sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("Dr. Sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("Doctor Sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("dr sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("sheila doctor"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("Dr. Dr Sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("Doctor Dr Sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("Dr. Dr. Sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("dr dr sheila"), "Dr. Sheila")
        self.assertEqual(clean_doctor_name("Dr. sharmila new"), "Dr. Sharmila")
        self.assertEqual(clean_doctor_name("డాక్టర్ ప్రియాంక గారు"), "Dr. ప్రియాంక")
        self.assertEqual(clean_doctor_name("Dr Dr"), "")
        self.assertEqual(clean_doctor_name("Doctor"), "")

    # =========================================================================
    # PART 2: Eliminate Invented Product (Bug 3)
    # =========================================================================
    # PART 2: Eliminate Invented Product (Bug 3)
    # =========================================================================
    def test_no_invented_product_in_capture(self):
        # User did NOT specify a product
        query = "I met Dr Rajesh today and he asked for sample brochures."
        res = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript=query,
        )
        self.assertTrue(res.get("pending_confirmation"))
        card = res.get("card_data", {})
        self.assertNotIn("General discussion", str(card.get("product")))
        self.assertEqual(card.get("product"), "Not specified")

    # =========================================================================
    # PART 3: Eliminate Raw Internal Key Dumps in UI (Bug 4)
    # =========================================================================
    def test_no_raw_internal_extraction_leakage(self):
        query = "Meet Dr Rajesh Friday at 3 PM."
        res = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript=query,
        )
        response_text = res.get("response", "")
        # Must not contain raw key value dumps like '\nHCP: Dr. Rajesh\nProduct: None'
        self.assertNotIn("HCP:", response_text)
        self.assertNotIn("Product: None", response_text)
        self.assertNotIn("Request: None", response_text)
        self.assertIn("Dr. Rajesh", response_text)

    # =========================================================================
    # PART 4: Strict Invariant Distinction (Interaction vs Followup vs Meeting)
    # =========================================================================
    def test_strict_intent_invariants(self):
        # 1. Past Interaction
        u1 = understand_user_request("I met Dr Rajesh today")
        self.assertEqual(u1.intent, INTENT_CAPTURE_MEETING)

        # 2. CRM Follow-up task
        u2 = understand_user_request("Follow up with Dr Rajesh next Friday")
        self.assertEqual(u2.intent, INTENT_CREATE_FOLLOWUP)

        # 3. Future Calendar Meeting
        u3 = understand_user_request("Meet Dr Rajesh Friday at 3 PM")
        self.assertEqual(u3.intent, INTENT_SCHEDULE_MEETING)

        # 4. Meeting + Reminder
        u4 = understand_user_request("Remind me to meet Dr Rajesh Friday at 3 PM")
        self.assertEqual(u4.intent, INTENT_SCHEDULE_MEETING)
        self.assertTrue(u4.reminder_display is not None or u4.reminder_minutes is not None)

    # =========================================================================
    # PART 5: Test A — Unknown Doctor with Meeting & Reminder
    # "i want you to remind me to meet dr sharmila on 28 sep 2026"
    # =========================================================================
    def test_unknown_doctor_asks_for_confirmation_not_blind_create(self):
        query = "i want you to remind me to meet dr sharmila on 28 sep 2026"
        res = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript=query,
        )
        # Should ask whether user wants to add new HCP since Dr Sharmila is not in DB
        self.assertTrue(res.get("needs_clarification"))
        self.assertIn("Sharmila", res.get("response", ""))
        self.assertIn("new doctor", res.get("response", "").lower())

    # =========================================================================
    # PART 6: Test B — Explicit New Doctor Registration
    # "I had new doctor Allergen and his specialization is Cardiology."
    # =========================================================================
    def test_explicit_new_doctor_creation(self):
        query = "I had new doctor Allergen and his specialization is Cardiology."
        res = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript=query,
        )
        self.assertTrue(res.get("pending_confirmation"))
        card = res.get("card_data", {})
        self.assertEqual(card.get("doctor_name"), "Dr. Allergen")
        self.assertEqual(card.get("specialization"), "Cardiology")
        self.assertTrue(card.get("is_new_hcp"))

    # =========================================================================
    # PART 7: Test C — Multi-Action Meeting with New Doctor
    # "I met a new doctor Dr Sheila at Apollo Hospital. Her phone is 94326891. Schedule a meeting next Tuesday at 11."
    # =========================================================================
    def test_multi_action_new_doctor_meeting(self):
        query = "I met a new doctor Dr Sheila at Apollo Hospital. Her phone is 94326891. Schedule a meeting next Tuesday at 11."
        res = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript=query,
        )
        self.assertTrue(res.get("pending_confirmation"))
        card = res.get("card_data", {})
        self.assertEqual(card.get("doctor_name"), "Dr. Sheila")
        self.assertEqual(card.get("hospital"), "Apollo Hospital")
        self.assertEqual(card.get("phone"), "94326891")
        self.assertTrue(card.get("is_new_hcp"))

    # =========================================================================
    # PART 8: Test D — Multi-Turn Scheduling Correction & Confirm
    # Turn 1: "Schedule a meeting with Dr Rajesh next Friday at 3 PM"
    # Turn 2: "Actually make it 4 PM and remind me 1 hour before"
    # Turn 3: "Confirm"
    # =========================================================================
    def test_multiturn_meeting_correction_and_confirm(self):
        # Turn 1: Initial proposal
        r1 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="Schedule a meeting with Dr Rajesh next Friday at 3 PM",
        )
        self.assertTrue(r1.get("pending_confirmation"))
        self.assertEqual(r1.get("card_data", {}).get("meeting_time_display"), "03:00 PM")

        # Turn 2: Correction
        r2 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="Actually make it 4 PM and remind me 1 hour before",
            current_hcp_id=r1.get("current_hcp_id"),
            current_hcp_name=r1.get("current_hcp_name"),
            pending_confirmation=r1.get("pending_confirmation", False),
            pending_action=r1.get("pending_action"),
        )
        self.assertTrue(r2.get("pending_confirmation"))
        card2 = r2.get("card_data", {})
        self.assertEqual(card2.get("meeting_time_display"), "04:00 PM")
        self.assertIn("hour", card2.get("reminder_display", "").lower())

        # Turn 3: Confirm
        r3 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="Confirm",
            current_hcp_id=r2.get("current_hcp_id"),
            current_hcp_name=r2.get("current_hcp_name"),
            pending_confirmation=r2.get("pending_confirmation", False),
            pending_action=r2.get("pending_action"),
        )
        self.assertFalse(r3.get("pending_confirmation"))
        self.assertIn("scheduled", r3.get("response", "").lower())

        # Verify DB schedule created
        m = self.db.query(ScheduledMeeting).filter(ScheduledMeeting.user_id == self.user_id).order_by(ScheduledMeeting.id.desc()).first()
        self.assertIsNotNone(m)
        self.assertEqual(m.hcp.doctor_name, "Dr. Rajesh Kumar")

    # =========================================================================
    # PART 9: Test E — Multi-Turn Doctor Inquiries & Anaphora
    # Turn 1: "Tell me about Dr Rajesh"
    # Turn 2: "When did I meet him?"
    # Turn 3: "What did we discuss with him?"
    # =========================================================================
    def test_multiturn_anaphora_and_inquiries(self):
        # Turn 1: Doctor lookup
        r1 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="Tell me about Dr Rajesh",
        )
        self.assertEqual(r1.get("card_data", {}).get("doctor_name"), "Dr. Rajesh Kumar")

        # Turn 2: Anaphora "him"
        r2 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="When did I meet him?",
            current_hcp_id=r1.get("current_hcp_id"),
            current_hcp_name=r1.get("current_hcp_name"),
        )
        self.assertIn("Dr. Rajesh Kumar", r2.get("response", ""))

        # Turn 3: Discussion query
        r3 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="What did we discuss with him?",
            current_hcp_id=r2.get("current_hcp_id") or r1.get("current_hcp_id"),
            current_hcp_name=r2.get("current_hcp_name") or r1.get("current_hcp_name"),
        )
        self.assertIn("Dr. Rajesh Kumar", r3.get("response", ""))

    # =========================================================================
    # PART 10: Test F — Context Override
    # Turn 1: "Tell me about Dr Rajesh"
    # Turn 2: "Not Rajesh. I meant Sharma"
    # =========================================================================
    def test_context_override(self):
        # Turn 1
        r1 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="Tell me about Dr Rajesh",
        )

        # Turn 2: Override
        r2 = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="Not Rajesh. I meant Sharma",
            current_hcp_id=r1.get("current_hcp_id"),
            current_hcp_name=r1.get("current_hcp_name"),
        )
        self.assertIn("Dr. Sharma", r2.get("response", ""))
        self.assertEqual(r2.get("current_hcp_name"), "Dr. Sharma")

    # =========================================================================
    # PART 11: Test G & H — My Day Briefing & Next Action
    # =========================================================================
    def test_my_day_briefing_and_next_action(self):
        # My Day Briefing
        r_brief = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="What is my plan for today?",
        )
        self.assertEqual(r_brief.get("card_data", {}).get("type"), "crm_brief_card")

        # Next Action Recommendation
        r_next = run_voice_copilot_graph(
            self.db,
            user_id=self.user_id,
            transcript="What should I do next?",
        )
        self.assertEqual(r_next.get("card_data", {}).get("type"), "next_action_card")


if __name__ == "__main__":
    unittest.main(verbosity=2)
