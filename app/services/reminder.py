"""
Reminder service — isolated, non-blocking.
All functions wrap DB calls safely so callers can use them inside try/except.

Cooldown schedule (reset on each explicit dismiss):
  snooze_count 0 → show any time (never been dismissed)
  snooze_count 1 → re-show after 2 minutes
  snooze_count 2 → re-show after 10 minutes
  snooze_count >= 3 → re-show after 15 minutes (hard cap)
"""
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.models.reminder import Reminder

# Cooldown delays indexed by snooze_count (last entry is the cap)
SNOOZE_DELAYS: List[int] = [2, 10, 15]  # minutes


def _next_show_time(reminder: Reminder) -> datetime:
    """
    Returns the earliest time this reminder may be shown.
    - Never dismissed (last_shown_at is None) → eligible from reminder_time onward
    - Dismissed N times → eligible after last_shown_at + delay[N-1]
    """
    if reminder.last_shown_at is None:
        return reminder.reminder_time

    count = max(0, (reminder.snooze_count or 1) - 1)
    delay_minutes = SNOOZE_DELAYS[min(count, len(SNOOZE_DELAYS) - 1)]
    return reminder.last_shown_at + timedelta(minutes=delay_minutes)


def get_due_reminders(db: Session) -> List[Reminder]:
    """
    READ-ONLY. Returns pending reminders that are eligible to be shown now.
    Does NOT write to the database. State is only updated by dismiss() / mark_done().
    """
    now = datetime.utcnow()
    candidates = (
        db.query(Reminder)
        .filter(Reminder.reminder_time <= now, Reminder.status == "pending")
        .order_by(Reminder.reminder_time.asc())
        .all()
    )
    return [r for r in candidates if _next_show_time(r) <= now]


def dismiss(db: Session, reminder_id: int) -> bool:
    """
    Snooze a reminder (explicit user action).
    - Updates last_shown_at = now
    - Increments snooze_count → next re-show will use a longer delay
    - Does NOT change status → reminder remains pending
    """
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        return False
    reminder.last_shown_at = datetime.utcnow()
    reminder.snooze_count = (reminder.snooze_count or 0) + 1
    db.add(reminder)
    db.commit()
    return True




def mark_done(db: Session, reminder_id: int) -> bool:
    """Mark a reminder as permanently done. Returns True if found."""
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not reminder:
        return False
    reminder.status = "done"
    db.add(reminder)
    db.commit()
    return True


def create_reminder(
    db: Session,
    title: str,
    related_type: str,
    related_id: int,
    reminder_time: datetime,
    description: str = None,
) -> Reminder:
    """
    Create a new reminder row and simulate an email alert via console print.
    Always call inside try/except so failures never break the caller.
    """
    reminder = Reminder(
        title=title,
        description=description,
        related_type=related_type,
        related_id=related_id,
        reminder_time=reminder_time,
        status="pending",
        snooze_count=0,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    # Simulated email alert — no SMTP, no background worker
    print(f"[EMAIL REMINDER] {title} (related: {related_type} #{related_id})")

    return reminder
