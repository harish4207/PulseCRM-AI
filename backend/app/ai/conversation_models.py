"""
Conversation Models: Evolving CRM Record & Stateful Conversation
===============================================================
Defines the structured semantic models for Ask PulseCRM's conversational
state machine and progressive CRM record draft evolution.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class HcpDraft(BaseModel):
    id: Optional[int] = None
    doctor_name: Optional[str] = None
    specialization: Optional[str] = None
    hospital: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_new_hcp: bool = False


class InteractionDraft(BaseModel):
    date: Optional[str] = None
    meeting_notes: Optional[str] = None
    products_discussed: Optional[str] = None
    doctor_request: Optional[str] = None
    sentiment: Optional[str] = "positive"


class FollowUpDraft(BaseModel):
    date: Optional[str] = None
    notes: Optional[str] = None


class MeetingDraft(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    reminder_minutes: Optional[int] = None
    reminder_display: Optional[str] = None


class EvolvingCrmRecord(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: str = "DRAFT"  # DRAFT, REQUIRES_CONFIRMATION, PROCESSING, COMPLETED, CANCELLED, FAILED
    operation: str = "UNKNOWN"  # CREATE_HCP, CAPTURE_INTERACTION, CREATE_FOLLOWUP, SCHEDULE_MEETING, MULTI_ACTION_PLAN
    hcp: Optional[HcpDraft] = None
    interaction: Optional[InteractionDraft] = None
    follow_up: Optional[FollowUpDraft] = None
    meeting: Optional[MeetingDraft] = None
    changes_applied: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    conflict_info: Optional[Dict[str, Any]] = None

    def merge_update(self, other: "EvolvingCrmRecord") -> "EvolvingCrmRecord":
        """Merge new delta updates into this draft, recording changes."""
        changes = list(self.changes_applied)
        
        # Merge HCP
        if other.hcp:
            if not self.hcp:
                self.hcp = other.hcp
                if other.hcp.doctor_name:
                    changes.append(f"Doctor: {other.hcp.doctor_name}")
            else:
                if other.hcp.id and not self.hcp.id:
                    self.hcp.id = other.hcp.id
                if other.hcp.doctor_name and other.hcp.doctor_name != self.hcp.doctor_name:
                    self.hcp.doctor_name = other.hcp.doctor_name
                    changes.append(f"Doctor updated to {other.hcp.doctor_name}")
                if other.hcp.hospital:
                    self.hcp.hospital = other.hcp.hospital
                if other.hcp.city:
                    self.hcp.city = other.hcp.city
                if other.hcp.specialization:
                    self.hcp.specialization = other.hcp.specialization
                if other.hcp.phone:
                    self.hcp.phone = other.hcp.phone
                    changes.append(f"Phone: {other.hcp.phone}")
                if other.hcp.email:
                    self.hcp.email = other.hcp.email
                    changes.append(f"Email: {other.hcp.email}")
                if other.hcp.is_new_hcp:
                    self.hcp.is_new_hcp = True

        # Merge Interaction
        if other.interaction:
            if not self.interaction:
                self.interaction = other.interaction
            else:
                if other.interaction.products_discussed:
                    self.interaction.products_discussed = other.interaction.products_discussed
                    changes.append(f"Product: {other.interaction.products_discussed}")
                if other.interaction.doctor_request:
                    self.interaction.doctor_request = other.interaction.doctor_request
                    changes.append(f"Request: {other.interaction.doctor_request}")
                if other.interaction.meeting_notes:
                    self.interaction.meeting_notes = other.interaction.meeting_notes
                if other.interaction.date:
                    self.interaction.date = other.interaction.date

        # Merge Follow Up
        if other.follow_up:
            if not self.follow_up:
                self.follow_up = other.follow_up
                if other.follow_up.date:
                    changes.append(f"Follow-up: {other.follow_up.date}")
            else:
                if other.follow_up.date:
                    self.follow_up.date = other.follow_up.date
                    changes.append(f"Follow-up updated to {other.follow_up.date}")
                if other.follow_up.notes:
                    self.follow_up.notes = other.follow_up.notes

        # Merge Meeting
        if other.meeting:
            if not self.meeting:
                self.meeting = other.meeting
            else:
                if other.meeting.date:
                    self.meeting.date = other.meeting.date
                    changes.append(f"Meeting date: {other.meeting.date}")
                if other.meeting.time:
                    self.meeting.time = other.meeting.time
                    changes.append(f"Meeting time: {other.meeting.time}")
                if other.meeting.location:
                    self.meeting.location = other.meeting.location
                if other.meeting.reminder_minutes is not None:
                    self.meeting.reminder_minutes = other.meeting.reminder_minutes
                    self.meeting.reminder_display = other.meeting.reminder_display
                    if other.meeting.reminder_minutes == 0:
                        changes.append("Removed reminder")
                    else:
                        changes.append(f"Reminder: {other.meeting.reminder_display}")

        # Combine actions
        combined_actions = list(set(self.actions + (other.actions or [])))
        self.actions = combined_actions
        self.changes_applied = changes
        if other.operation and other.operation != "UNKNOWN":
            self.operation = other.operation
        return self


class ConversationState(BaseModel):
    conversation_id: Optional[str] = None
    active_hcp_id: Optional[int] = None
    active_hcp_name: Optional[str] = None
    active_hospital: Optional[str] = None
    evolving_record: Optional[EvolvingCrmRecord] = None
    pending_confirmation: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    history: List[Dict[str, str]] = Field(default_factory=list)
    confidence: float = 1.0
    needs_clarification: bool = False
    clarification_type: Optional[str] = None
    ambiguous_candidates: List[Dict[str, Any]] = Field(default_factory=list)
