"""
Phase 22 Verification Suite: Persistent Conversation, Navigation & Responsive UI
================================================================================
Tests:
1. Navigation persistence (simulated route changes maintain active doctor context and anaphora).
2. Conversation ID reuse across multi-turn interactions.
3. Pending meeting review persistence and subsequent confirmation across route transitions.
4. Pending follow-up review persistence across route transitions.
5. Completed action card immutability (stays completed, no active confirmation buttons).
6. Action idempotency on preserved action IDs (0 duplicate DB records).
7. Reset conversation (+ New) boundary (clears active context and avoids stale doctor references).
8. Pronoun isolation after reset (anaphora does not carry over to fresh conversation).
9. Conversational My Day & Next Action reliability.
10. Error resilience (zero raw exceptions or leaked internal database keys).
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


class TestPhase22NavigationUISuite(unittest.TestCase):
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
    # Test 1: Multi-turn Navigation Persistence (Part 1 & 2)
    # ------------------------------------------------------------------------
    def test_navigation_persistence_maintains_context(self):
        conv_id = "test_conv_abc_123"
        # Turn 1: On Copilot page
        res1 = run_voice_copilot_graph(
            self.db,
            "Tell me about Dr Rajesh",
            user_id=1,
            conversation_id=conv_id,
        )
        self.assertEqual(res1.get("hcp_name"), "Dr. Rajesh Kumar")
        self.assertEqual(res1.get("hcp_id"), 1)

        # Simulated navigation: user visited /hcps, /interactions, /dashboard, then returned to /voice-copilot
        # Preserved context is passed back from CopilotContext
        res2 = run_voice_copilot_graph(
            self.db,
            "When did I last meet him?",
            user_id=1,
            conversation_id=conv_id,
            current_hcp_id=res1.get("hcp_id"),
            current_hcp_name=res1.get("hcp_name"),
            history=[
                {"role": "user", "content": "Tell me about Dr Rajesh"},
                {"role": "assistant", "content": res1.get("response", "")},
            ],
        )
        self.assertEqual(res2.get("hcp_id"), 1)
        self.assertEqual(res2.get("intent"), "GET_HCP_INTERACTIONS")

    # ------------------------------------------------------------------------
    # Test 2: Stable Conversation ID (Part 4)
    # ------------------------------------------------------------------------
    def test_conversation_id_reused_across_turns(self):
        conv_id = "stable_conv_uuid_789"
        res1 = run_voice_copilot_graph(self.db, "Tell me about Dr Sharma", user_id=1, conversation_id=conv_id)
        self.assertEqual(res1.get("conversation_id", conv_id), conv_id)

        # Subsequent query with same conv_id
        res2 = run_voice_copilot_graph(
            self.db,
            "What is his hospital?",
            user_id=1,
            conversation_id=conv_id,
            current_hcp_id=res1.get("hcp_id"),
            current_hcp_name=res1.get("hcp_name"),
        )
        self.assertEqual(res2.get("hcp_id"), 2)

    # ------------------------------------------------------------------------
    # Test 3: Pending Meeting Survives Navigation & Confirms (Part 6)
    # ------------------------------------------------------------------------
    def test_pending_meeting_survives_navigation(self):
        conv_id = "conv_meeting_review_456"
        # User proposes meeting
        res1 = run_voice_copilot_graph(
            self.db,
            "Meet Dr Rajesh Friday at 3 PM and remind me 30 minutes before",
            user_id=1,
            conversation_id=conv_id,
        )
        self.assertTrue(res1.get("pending_confirmation"))
        pending_act = res1.get("pending_action")
        self.assertIsNotNone(pending_act)
        self.assertEqual(len(self.db._meetings_store), 0)

        # User navigates to /hcps, /dashboard, and returns to /voice-copilot
        # The pending action survives and is confirmed
        res2 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            conversation_id=conv_id,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertFalse(res2.get("pending_confirmation"))
        self.assertIsNone(res2.get("pending_action"))
        self.assertEqual(len(self.db._meetings_store), 1)
        self.assertEqual(len(self.db._reminders_store), 1)

    # ------------------------------------------------------------------------
    # Test 4: Pending Follow-up Survives Navigation (Part 6)
    # ------------------------------------------------------------------------
    def test_pending_followup_survives_navigation(self):
        conv_id = "conv_fu_review_789"
        res1 = run_voice_copilot_graph(
            self.db,
            "Follow up with Dr Rajesh next Friday",
            user_id=1,
            conversation_id=conv_id,
        )
        self.assertTrue(res1.get("pending_confirmation"))
        pending_act = res1.get("pending_action")

        # Confirm after navigation
        res2 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            conversation_id=conv_id,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertFalse(res2.get("pending_confirmation"))
        self.assertIsNone(res2.get("pending_action"))

    # ------------------------------------------------------------------------
    # Test 5: Completed Action Card State Immutability (Part 7)
    # ------------------------------------------------------------------------
    def test_completed_card_state_immutability(self):
        res1 = run_voice_copilot_graph(
            self.db,
            "Meet Dr Rajesh Friday at 3 PM",
            user_id=1,
        )
        pending_act = res1.get("pending_action")

        res2 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        card = res2.get("card_data", {})
        self.assertEqual(card.get("status"), "completed")
        self.assertTrue(card.get("is_completed"))

    # ------------------------------------------------------------------------
    # Test 6: Idempotent Confirmation (Part 7)
    # ------------------------------------------------------------------------
    def test_idempotent_confirmation_on_preserved_action(self):
        res1 = run_voice_copilot_graph(
            self.db,
            "Meet Dr Rajesh Friday at 3 PM",
            user_id=1,
        )
        pending_act = res1.get("pending_action")

        res2 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertEqual(len(self.db._meetings_store), 1)

        # Repeated confirm
        res3 = run_voice_copilot_graph(
            self.db,
            "Confirm",
            user_id=1,
            pending_confirmation=True,
            pending_action=pending_act,
        )
        self.assertEqual(len(self.db._meetings_store), 1)
        self.assertIn("already confirmed", res3.get("response", "").lower())

    # ------------------------------------------------------------------------
    # Test 7: Reset Conversation (+ New) Clears Context (Part 3 & 25)
    # ------------------------------------------------------------------------
    def test_new_conversation_resets_context(self):
        # Conversation 1
        res1 = run_voice_copilot_graph(
            self.db,
            "Tell me about Dr Rajesh",
            user_id=1,
            conversation_id="conv_session_1",
        )
        self.assertEqual(res1.get("hcp_name"), "Dr. Rajesh Kumar")

        # User clicked "+ New", starting a fresh conversation session with null context
        res2 = run_voice_copilot_graph(
            self.db,
            "When did I last meet him?",
            user_id=1,
            conversation_id="conv_session_2_fresh",
            current_hcp_id=None,
            current_hcp_name=None,
            history=[],
        )
        # Should ask for doctor clarification rather than assuming Dr. Rajesh
        self.assertTrue(res2.get("needs_clarification") or "which doctor" in res2.get("response", "").lower() or not res2.get("hcp_id"))

    # ------------------------------------------------------------------------
    # Test 8: Conversational My Day when clear (Part 9)
    # ------------------------------------------------------------------------
    def test_conversational_my_day(self):
        res = run_voice_copilot_graph(self.db, "What do I have today?", user_id=1)
        self.assertIn("clear today", res.get("response", "").lower())

    # ------------------------------------------------------------------------
    # Test 9: Conversational Next Action (Part 10)
    # ------------------------------------------------------------------------
    def test_conversational_next_action(self):
        res = run_voice_copilot_graph(self.db, "What should I do next?", user_id=1)
        self.assertIn("up to date", res.get("response", "").lower())
        self.assertEqual(res.get("card_data", {}).get("type"), "next_action_card")

    # ------------------------------------------------------------------------
    # Test 10: Zero Raw Error Leakage (Part 21)
    # ------------------------------------------------------------------------
    def test_error_resilience_no_raw_leaks(self):
        # Database query failure simulation
        broken_db = MagicMock()
        broken_db.query.side_effect = Exception("DB Connection Timeout")
        res = run_voice_copilot_graph(broken_db, "Tell me about Dr Rajesh", user_id=1)
        resp = res.get("response", "")
        self.assertNotIn("Traceback", resp)
        self.assertNotIn("DB Connection Timeout", resp)
        self.assertNotIn("hcp_id", resp)


if __name__ == "__main__":
    unittest.main()
