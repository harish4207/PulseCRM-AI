import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.meeting_reminder import MeetingReminder
from app.models.scheduled_meeting import ScheduledMeeting
from app.models.hcp import HCP

logger = logging.getLogger(__name__)

_SCHEDULER_RUNNING = False
_SCHEDULER_TASK = None


async def reminder_worker_loop():
    global _SCHEDULER_RUNNING
    logger.info("[ReminderScheduler] Local background reminder worker started.")
    while _SCHEDULER_RUNNING:
        try:
            db: Session = SessionLocal()
            try:
                now = datetime.now()
                due_reminders = (
                    db.query(MeetingReminder)
                    .filter(
                        MeetingReminder.status == "pending",
                        MeetingReminder.remind_at <= now,
                    )
                    .all()
                )

                for rem in due_reminders:
                    meeting = db.query(ScheduledMeeting).filter(ScheduledMeeting.id == rem.meeting_id).first()
                    doc_name = "Doctor"
                    if meeting and meeting.hcp:
                        doc_name = meeting.hcp.doctor_name

                    time_disp = meeting.meeting_time_display if meeting else "scheduled time"
                    logger.info(
                        f"🔔 [REMINDER TRIGGERED] Meeting #{rem.meeting_id} with {doc_name} at {time_disp} (User #{rem.user_id})"
                    )
                    rem.status = "triggered"

                if due_reminders:
                    db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"[ReminderScheduler] Worker cycle error: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[ReminderScheduler] DB session error: {e}")

        await asyncio.sleep(20)


def start_reminder_scheduler():
    global _SCHEDULER_RUNNING, _SCHEDULER_TASK
    if _SCHEDULER_RUNNING:
        return
    _SCHEDULER_RUNNING = True
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            _SCHEDULER_TASK = asyncio.create_task(reminder_worker_loop())
    except Exception as e:
        logger.warning(f"[ReminderScheduler] Could not attach worker loop: {e}")


def stop_reminder_scheduler():
    global _SCHEDULER_RUNNING, _SCHEDULER_TASK
    _SCHEDULER_RUNNING = False
    if _SCHEDULER_TASK:
        _SCHEDULER_TASK.cancel()
        _SCHEDULER_TASK = None
