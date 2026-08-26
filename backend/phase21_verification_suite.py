"""
Phase 21 Verification Suite
============================
Tests:
1. Meeting card data contains full HCP metadata (hospital, city, specialization, location).
2. Post-confirmation state sets pending_confirmation=False, pending_action=None, is_completed=True.
3. Idempotent confirmations (repeated confirms yield exactly 1 meeting and 1 reminder).
4. Meeting conflict detection returns conflict_info and marks is_conflict=True for overlapping slots.
5. Invariant separation (CAPTURE_MEETING vs CREATE_FOLLOWUP vs SCHEDULE_MEETING).
6. Multi-turn anaphora and context override.
7. My Day conversational response when 0 tasks due.
8. Next Action prioritization and structured recommendations.
9. Unknown HCP prompts for confirmation rather than blind creation.
10. Product omission / No invented "General discussion".
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.meeting_reminder import MeetingReminder

from app.ai.normalizer import clean_doctor_name
from app.ai.llm_copilot_understanding import understand_user_request
from app.ai.fuzzy_matcher import match_hcp_from_db
from app.ai.voice_tools import (
    check_meeting_conflict,
    schedule_meeting,
    get_scheduled_meetings,
    get_crm_day_brief,
    get_next_action,
)
from app.ai.voice_copilot_graph import run_voice_copilot_graph, EXECUTED_ACTION_IDS


class TestPhase21Verification(unittest.TestCase):
    def setUp(self):
        EXECUTED_ACTION_IDS.clear()
        self.hcp1 = HCP(
            id=1,
            doctor_name="Dr. Rajesh Kumar",
            specialization="Cardiologist",
            hospital="Apollo Hospital",
            city="Visakhapatnam",
            phone="9876543210",
            email="rajesh@apollo.com",
        )
        self.hcp2 = HCP(
            id=2,
            doctor_name="Dr. Sharma",
            specialization="Neurologist",
            hospital="Care Hospital",
            city="Hyderabad",
            phone="9876543211",
            email="sharma@care.com",
        )
        self.hcp3 = HCP(
            id=3,
            doctor_name="Dr. Priyanka",
            specialization="Cardiologist",
            hospital="Apollo Hospital",
            city="Visakhapatnam",
            phone="9876543212",
            email="priyanka@apollo.com",
        )
        self.all_hcps = [self.hcp1, self.hcp2, self.hcp3]
        self.db = self._create_mock_db()

    def _create_mock_db(self):
        db = MagicMock()
        meetings_store = []
        reminders_store = []
        interactions_store = []

        def query_side_effect(*entities, **kwargs):
            q = MagicMock()
            model = entities[0] if entities else None

            if model is HCP or getattr(model, "__name__", "") == "HCP":
                q.all.return_value = self.all_hcps
                def filter_hcp(*args):
                    fq = MagicMock()
                    matched = self.all_hcps
                    for arg in args:
                        r_val = getattr(getattr(arg, "right", None), "value", None)
                        for h in self.all_hcps:
                            if r_val == h.id or r_val == h.doctor_name or f"={h.id}" in str(arg):
                                matched = [h]
                                break
                    fq.all.return_value = matched
                    fq.first.side_effect = lambda: (matched[0] if matched else None)
                    fq.count.return_value = len(matched)
                    fq.filter.side_effect = filter_hcp
                    return fq
                q.filter.side_effect = filter_hcp
                q.first.return_value = self.hcp1

            elif model is ScheduledMeeting or getattr(model, "__name__", "") == "ScheduledMeeting":
                q.all.side_effect = lambda: list(meetings_store)
                q.count.side_effect = lambda: len(meetings_store)
                def filter_sm(*args):
                    fq = MagicMock()
                    filtered = list(meetings_store)
                    for arg in args:
                        arg_str = str(arg)
                        r_val = getattr(getattr(arg, "right", None), "value", None)
                        if "user_id" in arg_str and r_val:
                            filtered = [m for m in filtered if m.user_id == r_val]
                        if "hcp_id" in arg_str and r_val:
                            filtered = [m for m in filtered if m.hcp_id == r_val]
                        if "status" in arg_str and r_val:
                            filtered = [m for m in filtered if m.status == r_val]
                    fq.all.side_effect = lambda: filtered
                    fq.first.side_effect = lambda: (filtered[0] if filtered else None)
                    fq.count.side_effect = lambda: len(filtered)
                    fq.order_by.return_value = fq
                    fq.filter.side_effect = filter_sm
                    return fq
                q.filter.side_effect = filter_sm
                q.order_by.return_value = q

            elif model is MeetingReminder or getattr(model, "__name__", "") == "MeetingReminder":
                q.all.side_effect = lambda: list(reminders_store)
                q.count.side_effect = lambda: len(reminders_store)
                def filter_mr(*args):
                    fq = MagicMock()
                    filtered = list(reminders_store)
                    fq.all.side_effect = lambda: filtered
                    fq.first.side_effect = lambda: (filtered[0] if filtered else None)
                    fq.count.side_effect = lambda: len(filtered)
                    fq.filter.side_effect = filter_mr
                    return fq
                q.filter.side_effect = filter_mr

            elif model is Interaction or getattr(model, "__name__", "") == "Interaction":
                q.all.side_effect = lambda: list(interactions_store)
                q.count.side_effect = lambda: len(interactions_store)
                def filter_in(*args):
                    fq = MagicMock()
                    filtered = list(interactions_store)
                    for arg in args:
                        arg_str = str(arg)
                        r_val = getattr(getattr(arg, "right", None), "value", None)
                        if "user_id" in arg_str and r_val:
                            filtered = [i for i in filtered if i.user_id == r_val]
                        if "hcp_id" in arg_str and r_val:
                            filtered = [i for i in filtered if i.hcp_id == r_val]
                    fq.all.side_effect = lambda: filtered
                    fq.first.side_effect = lambda: (filtered[0] if filtered else None)
                    fq.count.side_effect = lambda: len(filtered)
                    fq.order_by.return_value.limit.return_value.all.side_effect = lambda: filtered
                    fq.order_by.return_value.all.side_effect = lambda: filtered
                    fq.filter.side_effect = filter_in
                    return fq
                q.filter.side_effect = filter_in
                q.order_by.return_value = q

            return q

        def add_side_effect(obj):
            if isinstance(obj, ScheduledMeeting):
                if not getattr(obj, "id", None):
                    obj.id = len(meetings_store) + 1
                for h in self.all_hcps:
                    if h.id == obj.hcp_id:
                        obj.hcp = h
                        break
                meetings_store.append(obj)
            elif isinstance(obj, MeetingReminder):
                if not getattr(obj, "id", None):
                    obj.id = len(reminders_store) + 1
                reminders_store.append(obj)
            elif isinstance(obj, Interaction):
                if not getattr(obj, "id", None):
                    obj.id = len(interactions_store) + 1
                interactions_store.append(obj)

        db.query.side_effect = query_side_effect
        db.add.side_effect = add_side_effect
        db._meetings_store = meetings_store
        db._reminders_store = reminders_store
        db._interactions_store = interactions_store
        return db

    # ------------------------------------------------------------------------
    # Test 1: Full HCP Metadata in Meeting Review Cards (Part 2)
    # ------------------------------------------------------------------------
    def test_meeting_review_card_hcp_metadata(self):
        res = run_voice_copilot_graph(
            self.db,
            "Schedule a meeting with Dr Rajesh next Friday at 3 PM",
            user_id=1,
        )
        self.assertTrue(res.get("pending_confirmation"))
        card = res.get("card_data", {})
        self.assertEqual(card.get("doctor_name"), "Dr. Rajesh Kumar")
        self.assertEqual(card.get("hospital"), "Apollo Hospital")
        self.assertEqual(card.get("city"), "Visakhapatnam")
        self.assertEqual(card.get("location"), "Apollo Hospital · Visakhapatnam")
        self.assertIn("Apollo Hospital", res.get("response", ""))
        self.assertNotIn("Hospital Clinic", card.get("hospital", ""))

    # ------------------------------------------------------------------------
    # Test 2: Post-Confirmation Completed Card State (Part 3)
    # ------------------------------------------------------------------------
    def test_post_confirmation_state_transitions(self):
        # Step 1: Proposal
        res1 = run_voice_copilot_graph(
            self.db,
            "Meet Dr Rajesh Friday at 3 PM",
            user_id=1,
        )
        self.assertTrue(res1.get("pending_confirmation"))
        pending_act = res1.get("pending_action")

        # Step 2: Confirm
        res2 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertFalse(res2.get("pending_confirmation"))
        self.assertIsNone(res2.get("pending_action"))
        card = res2.get("card_data", {})
        self.assertEqual(card.get("type"), "meeting_schedule_card")
        self.assertEqual(card.get("status"), "completed")
        self.assertTrue(card.get("is_completed"))
        self.assertEqual(card.get("hospital"), "Apollo Hospital")
        self.assertEqual(len(self.db._meetings_store), 1)
        self.assertEqual(len(self.db._reminders_store), 1)

    # ------------------------------------------------------------------------
    # Test 3: Idempotent Confirmation (Part 4)
    # ------------------------------------------------------------------------
    def test_idempotent_repeated_confirmation(self):
        res1 = run_voice_copilot_graph(
            self.db,
            "Meet Dr Rajesh Friday at 3 PM",
            user_id=1,
        )
        pending_act = res1.get("pending_action")

        # First confirm
        res2 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertEqual(len(self.db._meetings_store), 1)

        # Repeated confirm with same action_id
        res3 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertEqual(len(self.db._meetings_store), 1)
        self.assertEqual(len(self.db._reminders_store), 1)
        self.assertIn("already confirmed", res3.get("response", "").lower())

    # ------------------------------------------------------------------------
    # Test 4: Meeting Conflict Detection (Part 5)
    # ------------------------------------------------------------------------
    def test_meeting_conflict_detection(self):
        # Schedule meeting 1 with Dr. Sharma on Aug 28 at 3:00 PM
        t_dt = datetime(2026, 8, 28, 15, 0)
        schedule_meeting(
            self.db,
            user_id=1,
            hcp_id=2,
            meeting_time=t_dt,
            meeting_time_display="August 28, 2026 at 03:00 PM",
            location="Care Hospital · Hyderabad",
        )

        # Check conflict when attempting to schedule Dr. Rajesh at 3:15 PM
        t_overlap = datetime(2026, 8, 28, 15, 15)
        conflict = check_meeting_conflict(self.db, user_id=1, target_time=t_overlap, hcp_id=1)
        self.assertTrue(conflict.get("is_conflict"))
        self.assertEqual(conflict.get("conflicting_meeting", {}).get("doctor_name"), "Dr. Sharma")

    # ------------------------------------------------------------------------
    # Test 5: Distinct Invariants (Part 6)
    # ------------------------------------------------------------------------
    def test_distinct_invariants(self):
        u1 = understand_user_request("I met Dr Rajesh today.")
        self.assertEqual(u1.intent, "CAPTURE_MEETING")

        u2 = understand_user_request("Follow up with Dr Rajesh next Friday.")
        self.assertEqual(u2.intent, "CREATE_FOLLOWUP")

        u3 = understand_user_request("Meet Dr Rajesh Friday at 3 PM.")
        self.assertEqual(u3.intent, "SCHEDULE_MEETING")

    # ------------------------------------------------------------------------
    # Test 6: Multi-turn Anaphora and Context Override (Part 7)
    # ------------------------------------------------------------------------
    def test_context_memory_and_override(self):
        # Step 1: Tell me about Dr Rajesh
        r1 = run_voice_copilot_graph(self.db, "Tell me about Dr Rajesh", user_id=1)
        self.assertEqual(r1.get("hcp_name"), "Dr. Rajesh Kumar")

        # Step 2: When did I meet him?
        r2 = run_voice_copilot_graph(
            self.db,
            "When did I meet him?",
            user_id=1,
            current_hcp_id=r1.get("hcp_id"),
            current_hcp_name=r1.get("hcp_name"),
        )
        self.assertEqual(r2.get("hcp_id"), 1)

        # Step 3: Override to Dr. Sharma
        r3 = run_voice_copilot_graph(
            self.db,
            "Not Rajesh. I meant Dr Sharma",
            user_id=1,
            current_hcp_id=r1.get("hcp_id"),
            current_hcp_name=r1.get("hcp_name"),
        )
        self.assertEqual(r3.get("hcp_id"), 2)
        self.assertEqual(r3.get("hcp_name"), "Dr. Sharma")

        # Step 4: When did I meet him? -> Now resolves to Dr. Sharma
        r4 = run_voice_copilot_graph(
            self.db,
            "When did I meet him?",
            user_id=1,
            current_hcp_id=r3.get("hcp_id"),
            current_hcp_name=r3.get("hcp_name"),
        )
        self.assertEqual(r4.get("hcp_id"), 2)

    # ------------------------------------------------------------------------
    # Test 7: My Day Conversational Response (Part 9)
    # ------------------------------------------------------------------------
    def test_my_day_conversational_response(self):
        res = run_voice_copilot_graph(self.db, "What is my plan for today?", user_id=1)
        self.assertIn("clear today", res.get("response", "").lower())
        self.assertEqual(res.get("card_data", {}).get("type"), "crm_brief_card")

    # ------------------------------------------------------------------------
    # Test 8: Next Action Structured Prioritization (Part 10)
    # ------------------------------------------------------------------------
    def test_next_action_recommendation(self):
        res = run_voice_copilot_graph(self.db, "What should I do next?", user_id=1)
        self.assertIn("up to date", res.get("response", "").lower())
        card = res.get("card_data", {})
        self.assertEqual(card.get("type"), "next_action_card")
        self.assertIn("action_items", card.get("next_action", {}))

    # ------------------------------------------------------------------------
    # Test 9: Unknown Doctor Confirmation Prompt (Part 16)
    # ------------------------------------------------------------------------
    def test_unknown_doctor_asks_confirmation(self):
        res = run_voice_copilot_graph(
            self.db,
            "Schedule a meeting with Dr Sharmila next Tuesday at 3",
            user_id=1,
        )
        self.assertTrue(res.get("needs_clarification"))
        self.assertIn("Dr. Sharmila", res.get("response", ""))
        self.assertEqual(len(self.db._meetings_store), 0)

    # ------------------------------------------------------------------------
    # Test 10: Zero Invented Products (Part 17)
    # ------------------------------------------------------------------------
    def test_zero_invented_products(self):
        res = run_voice_copilot_graph(
            self.db,
            "I met Dr Rajesh Kumar today at Apollo Hospital. Save this.",
            user_id=1,
        )
        card = res.get("card_data", {})
        self.assertEqual(card.get("product"), "Not specified")
        self.assertNotIn("General discussion", card.get("product", ""))


if __name__ == "__main__":
    unittest.main()
