# True Conversational CRM Agent Reliability Suite
# ===============================================
# Validates:
# 1. Temporal tokens rejection ('Dr. Today' bug prevention)
# 2. Incomplete information gate (0 DB writes, 0 confirmation cards without doctor name)
# 3. 10-turn progressive evolving record accumulation
# 4. Field-level evolution & modification (change time, reminder removal)
# 5. Entity replacement & zero-contamination across doctor shifts
# 6. Natural pronoun & anaphora resolution
# 7. Telugu / Mixed-language conversational support
# 8. Strict Atomic Transaction DB Gate (commits only on confirm, rollbacks cleanly)

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.meeting_reminder import MeetingReminder
from app.ai.normalizer import is_valid_person_name, clean_doctor_name
from app.ai.voice_copilot_graph import run_voice_copilot_graph


class MockDatabase:
    def __init__(self):
        self._hcps = []
        self._interactions = []
        self._meetings = []
        self._reminders = []

    def query(self, model):
        mock_q = MagicMock()
        if model == HCP:
            mock_q.all.side_effect = lambda: list(self._hcps)
            mock_q.filter.return_value.first.side_effect = lambda: self._hcps[0] if self._hcps else None
            mock_q.filter.return_value.all.side_effect = lambda: list(self._hcps)
        elif model == Interaction:
            mock_q.all.side_effect = lambda: list(self._interactions)
            mock_q.filter.return_value.all.side_effect = lambda: list(self._interactions)
            mock_q.filter.return_value.order_by.return_value.all.side_effect = lambda: list(self._interactions)
            mock_q.filter.return_value.order_by.return_value.limit.return_value.all.side_effect = lambda: list(self._interactions)
        elif model == ScheduledMeeting:
            mock_q.all.side_effect = lambda: list(self._meetings)
            mock_q.filter.return_value.all.side_effect = lambda: list(self._meetings)
            mock_q.filter.return_value.order_by.return_value.all.side_effect = lambda: list(self._meetings)
            mock_q.filter.return_value.order_by.return_value.limit.return_value.all.side_effect = lambda: list(self._meetings)
        elif model == MeetingReminder:
            mock_q.all.side_effect = lambda: list(self._reminders)
            mock_q.filter.return_value.all.side_effect = lambda: list(self._reminders)
        return mock_q

    def add(self, obj):
        if isinstance(obj, HCP):
            obj.id = len(self._hcps) + 1
            self._hcps.append(obj)
        elif isinstance(obj, Interaction):
            obj.id = len(self._interactions) + 1
            if not getattr(obj, 'created_at', None):
                obj.created_at = datetime.now().isoformat()
            self._interactions.append(obj)
        elif isinstance(obj, ScheduledMeeting):
            obj.id = len(self._meetings) + 1
            self._meetings.append(obj)
        elif isinstance(obj, MeetingReminder):
            obj.id = len(self._reminders) + 1
            self._reminders.append(obj)

    def commit(self): pass
    def rollback(self): pass
    def flush(self): pass
    def refresh(self, obj): pass


class ConversationalCrmAgentReliabilityTests(unittest.TestCase):

    def setUp(self):
        self.db = MockDatabase()

    def test_01_reject_temporal_words_as_names(self):
        '''Test Section 1: Temporal words must NEVER produce Dr. Today or phantom HCPs.'''
        self.assertFalse(is_valid_person_name('today'))
        self.assertFalse(is_valid_person_name('tomorrow'))
        self.assertFalse(is_valid_person_name('yesterday'))
        self.assertFalse(is_valid_person_name('Friday'))
        self.assertFalse(is_valid_person_name('someone'))
        self.assertFalse(is_valid_person_name('Dr. Today'))
        self.assertTrue(is_valid_person_name('Dr. Ananya Rao'))
        self.assertTrue(is_valid_person_name('Kavya Reddy'))

        # Turn 1: 'I just met a new doctor today.'
        r = run_voice_copilot_graph(self.db, 'I just met a new doctor today.', user_id=1)
        self.assertTrue(r.get('needs_clarification'))
        self.assertIn('name', r.get('response', '').lower())
        self.assertNotIn('Dr. Today', str(r))
        self.assertEqual(len(self.db._hcps), 0)
        self.assertFalse(r.get('pending_confirmation', False))

    def test_02_full_10_turn_conversation_flow(self):
        '''Test Section 17 verbatim 10-turn real conversation flow.'''
        ctx = {}

        # Turn 1: 'I just met a new doctor today.'
        r1 = run_voice_copilot_graph(self.db, 'I just met a new doctor today.', user_id=1, **ctx)
        self.assertTrue(r1.get('needs_clarification'))
        self.assertIn('name', r1.get('response', '').lower())
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r1.get('current_hcp_id'),
            'current_hcp_name': r1.get('current_hcp_name'),
            'pending_action': r1.get('pending_action'),
            'pending_confirmation': r1.get('pending_confirmation', False),
        }

        # Turn 2: 'Her name is Dr Ananya Rao.'
        r2 = run_voice_copilot_graph(self.db, 'Her name is Dr Ananya Rao.', user_id=1, **ctx)
        self.assertIn('Ananya Rao', r2.get('response', ''))
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r2.get('current_hcp_id'),
            'current_hcp_name': r2.get('current_hcp_name'),
            'pending_action': r2.get('pending_action'),
            'pending_confirmation': r2.get('pending_confirmation', False),
        }

        # Turn 3: 'She is a cardiologist at KIMS Hospital in Hyderabad.'
        r3 = run_voice_copilot_graph(self.db, 'She is a cardiologist at KIMS Hospital in Hyderabad.', user_id=1, **ctx)
        act3 = r3.get('pending_action') or {}
        self.assertEqual(act3.get('hospital'), 'KIMS Hospital')
        self.assertEqual(act3.get('specialization'), 'Cardiologist')
        self.assertEqual(act3.get('city'), 'Hyderabad')
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r3.get('current_hcp_id'),
            'current_hcp_name': r3.get('current_hcp_name'),
            'pending_action': r3.get('pending_action'),
            'pending_confirmation': r3.get('pending_confirmation', False),
        }

        # Turn 4: 'Her phone is 9876543210.'
        r4 = run_voice_copilot_graph(self.db, 'Her phone is 9876543210.', user_id=1, **ctx)
        act4 = r4.get('pending_action') or {}
        self.assertEqual(act4.get('phone'), '9876543210')
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r4.get('current_hcp_id'),
            'current_hcp_name': r4.get('current_hcp_name'),
            'pending_action': r4.get('pending_action'),
            'pending_confirmation': r4.get('pending_confirmation', False),
        }

        # Turn 5: 'We discussed CardioPress-50 and she wants the clinical brochure.'
        r5 = run_voice_copilot_graph(self.db, 'We discussed CardioPress-50 and she wants the clinical brochure.', user_id=1, **ctx)
        act5 = r5.get('pending_action') or {}
        self.assertEqual(act5.get('products_discussed'), 'CardioPress-50')
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r5.get('current_hcp_id'),
            'current_hcp_name': r5.get('current_hcp_name'),
            'pending_action': r5.get('pending_action'),
            'pending_confirmation': r5.get('pending_confirmation', False),
        }

        # Turn 6: 'Let us meet next Friday at 3.'
        r6 = run_voice_copilot_graph(self.db, 'Let us meet next Friday at 3.', user_id=1, **ctx)
        act6 = r6.get('pending_action') or {}
        self.assertEqual(act6.get('meeting_time_display'), '03:00 PM')
        self.assertTrue(r6.get('pending_confirmation'))
        self.assertIsNotNone(r6.get('card_data'))
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r6.get('current_hcp_id'),
            'current_hcp_name': r6.get('current_hcp_name'),
            'pending_action': r6.get('pending_action'),
            'pending_confirmation': r6.get('pending_confirmation', False),
        }

        # Turn 7: 'Actually make it 4.'
        r7 = run_voice_copilot_graph(self.db, 'Actually make it 4.', user_id=1, **ctx)
        act7 = r7.get('pending_action') or {}
        self.assertEqual(act7.get('meeting_time_display'), '04:00 PM')
        self.assertEqual(act7.get('hcp_name'), 'Dr. Ananya Rao')
        self.assertEqual(act7.get('hospital'), 'KIMS Hospital')
        self.assertEqual(act7.get('phone'), '9876543210')
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r7.get('current_hcp_id'),
            'current_hcp_name': r7.get('current_hcp_name'),
            'pending_action': r7.get('pending_action'),
            'pending_confirmation': r7.get('pending_confirmation', False),
        }

        # Turn 8: 'Remind me one hour before.'
        r8 = run_voice_copilot_graph(self.db, 'Remind me one hour before.', user_id=1, **ctx)
        act8 = r8.get('pending_action') or {}
        self.assertEqual(act8.get('reminder_display'), '1 hour before')
        self.assertEqual(act8.get('meeting_time_display'), '04:00 PM')
        self.assertEqual(len(self.db._hcps), 0)
        ctx = {
            'current_hcp_id': r8.get('current_hcp_id'),
            'current_hcp_name': r8.get('current_hcp_name'),
            'pending_action': r8.get('pending_action'),
            'pending_confirmation': r8.get('pending_confirmation', False),
        }

        # Turn 9: 'Confirm.'
        r9 = run_voice_copilot_graph(self.db, 'Confirm.', user_id=1, **ctx)
        self.assertEqual(len(self.db._hcps), 1)
        self.assertEqual(len(self.db._interactions), 1)
        self.assertEqual(len(self.db._meetings), 1)
        self.assertEqual(len(self.db._reminders), 1)
        self.assertEqual(self.db._hcps[0].doctor_name, 'Dr. Ananya Rao')
        self.assertEqual(self.db._hcps[0].hospital, 'KIMS Hospital')
        self.assertEqual(self.db._hcps[0].phone, '9876543210')

        # Turn 10: 'What was my last interaction with her?'
        ctx_post = {
            'current_hcp_id': self.db._hcps[0].id,
            'current_hcp_name': self.db._hcps[0].doctor_name,
            'pending_action': None,
            'pending_confirmation': False,
        }
        r10 = run_voice_copilot_graph(self.db, 'What was my last interaction with her?', user_id=1, **ctx_post)
        self.assertIn('Dr. Ananya Rao', r10.get('response', ''))

    def test_03_entity_replacement_no_contamination(self):
        '''Test Section 13: Doctor shift resets draft metadata and avoids data contamination.'''
        hcp_suresh = HCP(id=10, doctor_name='Dr. Suresh', hospital='Apollo Hospital', specialization='Neurologist', phone='1111111111')
        self.db._hcps.append(hcp_suresh)

        ctx = {
            'current_hcp_id': 10,
            'current_hcp_name': 'Dr. Suresh',
            'current_hospital': 'Apollo Hospital',
        }

        # User introduces a new doctor: 'Actually I just met Dr Meera Reddy at Care Hospital.'
        r = run_voice_copilot_graph(self.db, 'Actually I just met Dr Meera Reddy at Care Hospital.', user_id=1, **ctx)
        act = r.get('pending_action') or {}
        self.assertEqual(act.get('hcp_name'), 'Dr. Meera Reddy')
        self.assertEqual(act.get('hospital'), 'Care Hospital')
        self.assertIsNone(act.get('hcp_id'))

    def test_04_reminder_removal(self):
        '''Test Section 4: User removes reminder (Don't remind me).'''
        pending = {
            'action_id': 'test1234',
            'type': 'SCHEDULE_MEETING',
            'hcp_name': 'Dr. Ramesh',
            'hospital': 'Apollo',
            'meeting_date_display': 'Friday',
            'meeting_time_display': '03:00 PM',
            'reminder_display': '30 minutes before',
            'reminder_minutes': 30,
            'actions': ['CREATE_MEETING', 'CREATE_REMINDER'],
        }
        ctx = {
            'pending_action': pending,
            'pending_confirmation': True,
            'current_hcp_name': 'Dr. Ramesh',
        }

        r = run_voice_copilot_graph(self.db, "Don't remind me.", user_id=1, **ctx)
        act = r.get('pending_action') or {}
        self.assertEqual(act.get('reminder_display'), 'No reminder')
        self.assertEqual(act.get('reminder_minutes'), 0)
        self.assertNotIn('CREATE_REMINDER', act.get('actions', []))
        self.assertEqual(act.get('meeting_time_display'), '03:00 PM')

    def test_05_telugu_multi_turn_flow(self):
        '''Test Telugu multi-turn conversation and confirmation.'''
        # Turn 1: 'Ippude kotha doctor ni kalisanu' (Met new doctor)
        r1 = run_voice_copilot_graph(self.db, 'Ippude kotha doctor ni kalisanu', user_id=1)
        self.assertTrue(r1.get('needs_clarification'))
        self.assertIn('డాక్టర్', r1.get('response', ''))

        ctx = {
            'pending_action': r1.get('pending_action'),
            'pending_confirmation': False,
        }

        # Turn 2: 'Aavida peru Dr Kavya Reddy'
        r2 = run_voice_copilot_graph(self.db, 'Aavida peru Dr Kavya Reddy', user_id=1, **ctx)
        self.assertIn('Dr. Kavya Reddy', str(r2.get('pending_action', {})))


if __name__ == '__main__':
    unittest.main(verbosity=2)
