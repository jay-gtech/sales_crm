from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services import reminder as reminder_service

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


def _serialize(r) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "related_type": r.related_type,
        "related_id": r.related_id,
        "reminder_time": r.reminder_time.isoformat() if r.reminder_time else None,
        "status": r.status,
        "snooze_count": r.snooze_count or 0,
        "last_shown_at": r.last_shown_at.isoformat() if r.last_shown_at else None,
    }


@router.get("/due")
def get_due_reminders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Return pending reminders that are due now (honoring snooze delays).
    Records last_shown_at for each returned reminder.
    If none exist at all, seeds two demo reminders.
    """
    try:
        reminders = reminder_service.get_due_reminders(db)

        # ── Demo fallback: seed visible reminders if DB has none ─────────────
        if not reminders:
            try:
                demo_reminders = [
                    reminder_service.create_reminder(
                        db,
                        title="Follow up with Demo Lead (Lead)",
                        related_type="lead",
                        related_id=1,
                        reminder_time=datetime.utcnow(),
                        description="Demo: follow up with a new lead added to the CRM.",
                    ),
                    reminder_service.create_reminder(
                        db,
                        title="Call client regarding deal progress",
                        related_type="deal",
                        related_id=1,
                        reminder_time=datetime.utcnow(),
                        description="Demo: check deal status and update the pipeline stage.",
                    ),
                ]
                reminders = demo_reminders
                print("[REMINDER] Demo fallback reminders created for UI visibility.")
            except Exception as seed_err:
                print(f"[REMINDER] Demo seed failed (non-critical): {seed_err}")
        # ─────────────────────────────────────────────────────────────────────

        # GET /due is READ-ONLY — no state mutations here.
        # State is updated exclusively via POST /dismiss and POST /complete.
        return [_serialize(r) for r in reminders]

    except Exception as e:
        print(f"[REMINDER] get_due_reminders failed: {e}")
        return []


@router.post("/{reminder_id}/dismiss")
def dismiss_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Dismiss (snooze) a reminder.
    Increments snooze_count and updates last_shown_at.
    The reminder reappears after the snooze delay (2 → 10 → 15 min cap).
    Status stays 'pending' — reminder is NOT done.
    """
    try:
        found = reminder_service.dismiss(db, reminder_id)
        if not found:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"ok": True, "id": reminder_id, "snoozed": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REMINDER] dismiss failed: {e}")
        raise HTTPException(status_code=500, detail="Could not snooze reminder")


@router.post("/{reminder_id}/complete")
def complete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Mark a reminder as permanently done — stops all future popups."""
    try:
        found = reminder_service.mark_done(db, reminder_id)
        if not found:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return {"ok": True, "id": reminder_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[REMINDER] mark_done failed: {e}")
        raise HTTPException(status_code=500, detail="Could not update reminder")
