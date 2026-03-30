"""
Action Handler — validates and executes structured CRM actions from the AI assistant.

Supported actions:
  create_lead   — creates a Lead record
  add_reminder  — creates a Reminder record (+ optional email notification)
  create_deal   — creates a Deal record (requires a contact; skipped gracefully if none exist)

Every function returns:
  {"ok": True,  "message": str, "link": str | None}   on success
  {"ok": False, "message": str, "link": None}          on failure

All handlers are async so ai_router can await execute_action safely.
Never raises — all exceptions are caught and returned as ok=False.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ok(message: str, link: str = None) -> Dict:
    return {"ok": True, "message": message, "link": link}

def _fail(message: str) -> Dict:
    return {"ok": False, "message": message, "link": None}


def _parse_time(value: Any) -> datetime:
    """
    Try to parse an ISO-8601 string.
    Falls back to tomorrow 09:00 UTC if the value is missing or unparseable.
    """
    if not value:
        raise ValueError("no value")
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            pass
    raise ValueError(f"unparseable datetime: {value!r}")


# ── action handlers ───────────────────────────────────────────────────────────

async def _handle_create_lead(params: Dict, db: Session, _user) -> Dict:
    try:
        from app.schemas.lead import LeadCreate
        from app.services.lead import create_lead as svc_create_lead

        first_name = (params.get("first_name") or "Unknown").strip()
        last_name  = (params.get("last_name")  or "Lead").strip()

        # email is required by LeadCreate — use a placeholder if omitted
        email = (params.get("email") or "").strip()
        if not email:
            slug = f"{first_name.lower()}.{last_name.lower()}".replace(" ", "")
            email = f"{slug}@placeholder.crm"

        lead_data = LeadCreate(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=params.get("phone") or None,
            company=params.get("company") or None,
            status=params.get("status") or "New",
        )
        lead = svc_create_lead(db, lead_data)
        return _ok(
            f"Lead **{first_name} {last_name}** created successfully.",
            link=f"/leads/{lead.id}",
        )
    except Exception as exc:
        logger.error("[action] create_lead failed: %s", exc)
        return _fail("Could not create the lead. Please try again or add it manually.")


async def _handle_add_reminder(params: Dict, db: Session, user) -> Dict:
    try:
        from app.services.reminder import create_reminder

        title = (params.get("title") or "Follow up").strip()[:100]

        # Parse the reminder time; fall back to tomorrow 09:00 UTC
        try:
            reminder_time = _parse_time(params.get("reminder_time"))
        except ValueError:
            reminder_time = datetime.utcnow().replace(
                hour=9, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

        description = params.get("description") or None

        create_reminder(
            db,
            title,
            "general",  # related_type
            0,          # related_id (no specific record)
            reminder_time,
            description,
        )
        time_str = reminder_time.strftime("%b %d, %Y at %H:%M")

        # ── Optional email notification — safe, never blocks action success ──
        try:
            if getattr(user, "email", None):
                from app.services.email_service import send_email_async
                subject = f"Reminder Set: {title}"
                body = (
                    f"Hello {getattr(user, 'display_name', user.email)},\n\n"
                    f"A reminder has been set:\n\n"
                    f"Title: {title}\n"
                    f"Time:  {time_str}\n"
                    f"Notes: {description or 'N/A'}"
                )
                await send_email_async(user.email, subject, body)
        except Exception as email_exc:
            logger.warning("[action] reminder email notification failed: %s", email_exc)

        return _ok(f"Reminder **\"{title}\"** set for {time_str}.")
    except Exception as exc:
        logger.error("[action] add_reminder failed: %s", exc)
        return _fail("Could not create the reminder. Please try again or add it manually.")


async def _handle_create_deal(params: Dict, db: Session, user) -> Dict:
    try:
        from app.models.contact import Contact
        from app.schemas.deal import DealCreate
        from app.services.deal import create_deal as svc_create_deal

        name = (params.get("name") or "New Deal").strip()[:120]

        # contact_id is required by DealCreate — use the first available contact
        contact = db.query(Contact).first()
        if contact is None:
            return _fail(
                "Could not create the deal — no contacts exist yet. "
                "Please add a contact first, then create the deal manually."
            )

        deal_data = DealCreate(
            name=name,
            amount=float(params.get("amount") or 0),
            stage=params.get("stage") or "New",
            contact_id=contact.id,
            owner_id=user.id,
        )
        deal = svc_create_deal(db, deal_data, user.id)
        return _ok(
            f"Deal **\"{name}\"** created successfully.",
            link=f"/deals/{deal.id}",
        )
    except Exception as exc:
        logger.error("[action] create_deal failed: %s", exc)
        return _fail("Could not create the deal. Please try again or add it manually.")


# ── dispatch ──────────────────────────────────────────────────────────────────

_HANDLERS = {
    "create_lead":  _handle_create_lead,
    "add_reminder": _handle_add_reminder,
    "create_deal":  _handle_create_deal,
}


async def execute_action(action_data: Dict, db: Session, user) -> Dict:
    """
    Execute a validated action dict from llm_service.extract_action.
    Returns {"ok": bool, "message": str, "link": str | None}.
    Async so ai_router can safely await it.
    Never raises.
    """
    if not action_data:
        return _fail("No action could be determined from your request.")

    action  = action_data.get("action")
    params  = action_data.get("params") or {}

    handler = _HANDLERS.get(action)
    if handler is None:
        return _fail(f"Action \"{action}\" is not supported yet.")

    try:
        return await handler(params, db, user)
    except Exception as exc:
        logger.error("[action] unhandled error in %s: %s", action, exc)
        return _fail("Something went wrong while executing that action. Please try manually.")
