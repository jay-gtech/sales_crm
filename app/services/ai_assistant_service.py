"""
AI Assistant Service — Zoho Zia-style global CRM assistant.

Parses natural language queries and returns structured responses
pulling live data from all CRM modules.

Never raises — always returns a valid dict so the endpoint stays safe.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.lead import Lead
from app.models.reminder import Reminder

logger = logging.getLogger(__name__)

# ── Intent detection ──────────────────────────────────────────────────────────

_INTENTS: Dict[str, List[str]] = {
    "leads":      ["lead", "prospect", "new contact", "lead count"],
    "deals":      ["deal", "opportunit", "pipeline", "stage", "revenue", "amount", "sale"],
    "activities": ["activit", "task", "log", "call log", "email log", "meeting log"],
    "reminders":  ["reminder", "follow up", "followup", "due", "overdue", "scheduled"],
    "contacts":   ["contact", "customer", "client", "account"],
    "insights":   ["insight", "summary", "overview", "health", "analytic", "report", "stat",
                   "dashboard", "how are", "performance"],
    "help":       ["help", "what can", "command", "option", "available", "what do you"],
    "actions":    ["action", "quick action", "navigate", "go to"],
}


def _detect_intent(q: str) -> str:
    for intent, keywords in _INTENTS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "general"


# ── Colour helpers ────────────────────────────────────────────────────────────

_LEAD_COLORS: Dict[str, str] = {
    "New": "blue", "Contacted": "indigo", "Qualified": "purple",
    "Proposal Sent": "amber", "Negotiation": "orange",
    "Converted": "green", "Lost": "red",
}
_DEAL_COLORS: Dict[str, str] = {
    "New": "slate", "Qualification": "blue", "Needs Analysis": "indigo",
    "Proposal": "violet", "Negotiation": "amber",
    "Closed Won": "green", "Closed Lost": "red",
}


# ── Intent handlers ───────────────────────────────────────────────────────────

def _leads(db: Session) -> Dict:
    total = db.query(func.count(Lead.id)).scalar() or 0
    statuses = ["New", "Contacted", "Qualified", "Proposal Sent",
                "Negotiation", "Converted", "Lost"]
    by_status = {
        s: (db.query(func.count(Lead.id)).filter(Lead.status == s).scalar() or 0)
        for s in statuses
    }
    recent = db.query(Lead).order_by(Lead.id.desc()).limit(5).all()

    items = [
        {
            "label": f"{l.first_name} {l.last_name}".strip(),
            "value": l.status or "New",
            "sub": l.company or "",
            "link": f"/leads/{l.id}",
            "color": _LEAD_COLORS.get(l.status, "gray"),
        }
        for l in recent
    ]

    active_count = sum(v for k, v in by_status.items() if k not in ("Converted", "Lost"))
    status_parts = [f"{v} {k}" for k, v in by_status.items() if v > 0]
    msg = (
        f"You have **{total}** leads total "
        f"({active_count} active).\n\n"
        + (", ".join(status_parts) if status_parts else "No leads yet.")
    )
    if items:
        msg += "\n\nMost recent:"

    return {
        "message": msg,
        "items": items or None,
        "links": [{"label": "→ View All Leads", "url": "/leads"}],
        "type": "list",
    }


def _deals(db: Session) -> Dict:
    total = db.query(func.count(Deal.id)).scalar() or 0
    pipeline_val = (
        db.query(func.sum(Deal.amount))
        .filter(Deal.stage.notin_(["Closed Lost"]))
        .scalar() or 0
    )
    won_val = (
        db.query(func.sum(Deal.amount)).filter(Deal.stage == "Closed Won").scalar() or 0
    )
    active = (
        db.query(func.count(Deal.id))
        .filter(Deal.stage.notin_(["Closed Won", "Closed Lost"]))
        .scalar() or 0
    )
    recent = db.query(Deal).order_by(Deal.id.desc()).limit(5).all()

    items = [
        {
            "label": d.name,
            "value": d.stage,
            "sub": f"${d.amount:,.0f}" if d.amount else "$0",
            "link": f"/deals/{d.id}",
            "color": _DEAL_COLORS.get(d.stage, "gray"),
        }
        for d in recent
    ]

    msg = (
        f"Pipeline: **{total}** deals, **${pipeline_val:,.0f}** total value "
        f"({active} active)."
    )
    if won_val > 0:
        msg += f" **${won_val:,.0f}** already won. 🎉"
    if items:
        msg += "\n\nRecent deals:"

    return {
        "message": msg,
        "items": items or None,
        "links": [{"label": "→ View Pipeline", "url": "/deals"}],
        "type": "list",
    }


def _activities(db: Session) -> Dict:
    pending   = db.query(func.count(Activity.id)).filter(Activity.status == "pending").scalar() or 0
    completed = db.query(func.count(Activity.id)).filter(Activity.status == "completed").scalar() or 0
    recent_p  = db.query(Activity).filter(Activity.status == "pending").order_by(Activity.id.desc()).limit(5).all()

    items = [
        {
            "label": (a.title or (a.description[:40] if a.description else "Untitled")),
            "value": a.activity_type or "Task",
            "sub": "pending",
            "link": "/activities",
            "color": "amber",
        }
        for a in recent_p
    ]

    msg = f"**{pending}** pending, **{completed}** completed activities."
    if pending == 0:
        msg += " All caught up! ✓"
    elif items:
        msg += "\n\nPending:"

    return {
        "message": msg,
        "items": items or None,
        "links": [{"label": "→ View Activities", "url": "/activities"}],
        "type": "list",
    }


def _reminders(db: Session) -> Dict:
    now     = datetime.utcnow()
    pending = db.query(Reminder).filter(Reminder.status == "pending").order_by(Reminder.reminder_time).limit(8).all()
    total_p = db.query(func.count(Reminder.id)).filter(Reminder.status == "pending").scalar() or 0

    items = []
    overdue_count = 0
    for r in pending:
        is_over = r.reminder_time and r.reminder_time < now
        if is_over:
            overdue_count += 1
        items.append({
            "label": r.title,
            "value": "Overdue" if is_over else "Upcoming",
            "sub": r.reminder_time.strftime("%b %d %H:%M") if r.reminder_time else "",
            "link": None,
            "color": "red" if is_over else "blue",
        })

    msg = f"**{total_p}** pending reminders."
    if overdue_count:
        msg += f" ⚠️ **{overdue_count}** overdue."
    if not pending:
        msg = "No pending reminders. You're all caught up! ✓"

    return {
        "message": msg,
        "items": items or None,
        "links": [],
        "type": "list",
    }


def _contacts(db: Session) -> Dict:
    total  = db.query(func.count(Contact.id)).scalar() or 0
    recent = db.query(Contact).order_by(Contact.id.desc()).limit(5).all()

    items = [
        {
            "label": f"{c.first_name or ''} {c.last_name or ''}".strip() or "Unknown",
            "value": c.account_name or c.title or "",
            "sub": c.email or c.phone or "",
            "link": "/contacts",
            "color": "green",
        }
        for c in recent
    ]

    msg = f"You have **{total}** contacts."
    if items:
        msg += "\n\nRecent contacts:"

    return {
        "message": msg,
        "items": items or None,
        "links": [{"label": "→ View Contacts", "url": "/contacts"}],
        "type": "list",
    }


def _insights(db: Session) -> Dict:
    total_leads   = db.query(func.count(Lead.id)).scalar() or 0
    active_deals  = (
        db.query(func.count(Deal.id))
        .filter(Deal.stage.notin_(["Closed Won", "Closed Lost"]))
        .scalar() or 0
    )
    won_deals     = db.query(func.count(Deal.id)).filter(Deal.stage == "Closed Won").scalar() or 0
    pipeline_val  = (
        db.query(func.sum(Deal.amount))
        .filter(Deal.stage.notin_(["Closed Lost"]))
        .scalar() or 0
    )
    pending_acts  = db.query(func.count(Activity.id)).filter(Activity.status == "pending").scalar() or 0
    pending_rems  = db.query(func.count(Reminder.id)).filter(Reminder.status == "pending").scalar() or 0
    total_contacts= db.query(func.count(Contact.id)).scalar() or 0
    conv_rate     = round(won_deals / total_leads * 100, 1) if total_leads > 0 else 0.0

    items = [
        {"label": "Total Leads",     "value": str(total_leads),    "sub": "in CRM",          "color": "blue"},
        {"label": "Active Deals",    "value": str(active_deals),   "sub": f"${pipeline_val:,.0f}", "color": "indigo"},
        {"label": "Won Deals",       "value": str(won_deals),      "sub": f"{conv_rate}% conv", "color": "green"},
        {"label": "Contacts",        "value": str(total_contacts), "sub": "total",           "color": "purple"},
        {"label": "Pending Tasks",   "value": str(pending_acts),   "sub": "activities",      "color": "amber"},
        {"label": "Reminders",       "value": str(pending_rems),   "sub": "pending",         "color": "red" if pending_rems else "gray"},
    ]

    today = datetime.utcnow().strftime("%b %d, %Y")
    msg   = (
        f"**CRM Health — {today}**\n\n"
        f"{total_leads} leads · {active_deals} active deals · "
        f"${pipeline_val:,.0f} pipeline · {conv_rate}% conversion rate."
    )
    if pending_acts:
        msg += f"\n\n⚡ {pending_acts} tasks need attention."
    if pending_rems:
        msg += f"  🔔 {pending_rems} reminders pending."

    return {
        "message": msg,
        "items": items,
        "links": [
            {"label": "→ Full Reports", "url": "/dashboard"},
            {"label": "→ Leads",        "url": "/leads"},
        ],
        "type": "summary",
    }


def _help() -> Dict:
    return {
        "message": "Here's what I can help you with:",
        "items": [
            {"label": "Leads",      "value": "query",    "sub": '"Show my leads" / "Lead count"',       "color": "blue"},
            {"label": "Deals",      "value": "pipeline", "sub": '"Active deals" / "Pipeline value"',    "color": "indigo"},
            {"label": "Activities", "value": "tasks",    "sub": '"Pending tasks" / "Activities"',       "color": "amber"},
            {"label": "Reminders",  "value": "alerts",   "sub": '"Reminders" / "Follow-ups"',           "color": "red"},
            {"label": "Contacts",   "value": "clients",  "sub": '"Show contacts" / "My clients"',       "color": "green"},
            {"label": "Insights",   "value": "analytics","sub": '"CRM summary" / "Overview"',           "color": "purple"},
        ],
        "links": [],
        "type": "help",
    }


def _actions() -> Dict:
    return {
        "message": "Here are some quick actions:",
        "items": [
            {"label": "Add Lead",       "value": "→",  "sub": "Create a new lead",          "link": "/leads",      "color": "blue"},
            {"label": "View Pipeline",  "value": "→",  "sub": "See all deals by stage",     "link": "/deals",      "color": "indigo"},
            {"label": "Log Activity",   "value": "→",  "sub": "Record a call or email",     "link": "/activities", "color": "amber"},
            {"label": "View Reports",   "value": "→",  "sub": "Analytics & insights",       "link": "/dashboard",  "color": "purple"},
            {"label": "Manage Contacts","value": "→",  "sub": "View your contacts",         "link": "/contacts",   "color": "green"},
        ],
        "links": [],
        "type": "actions",
    }


# ── Public entry point ────────────────────────────────────────────────────────

def process_assistant_query(query: str, db: Session, user: Any) -> Dict:
    """
    Process a natural language query against live CRM data.
    Returns a dict with: message (str), items (list|None), links (list), type (str).
    Never raises.
    """
    try:
        intent = _detect_intent(query.lower().strip())
        handlers = {
            "leads":      lambda: _leads(db),
            "deals":      lambda: _deals(db),
            "activities": lambda: _activities(db),
            "reminders":  lambda: _reminders(db),
            "contacts":   lambda: _contacts(db),
            "insights":   lambda: _insights(db),
            "help":       _help,
            "actions":    _actions,
        }
        if intent in handlers:
            return handlers[intent]()

        # General fallback
        return {
            "message": (
                "I'm not sure about that. Try asking:\n\n"
                "• **Leads** — \"Show my leads\"\n"
                "• **Deals** — \"Active deals\" or \"Pipeline\"\n"
                "• **Activities** — \"Pending tasks\"\n"
                "• **Reminders** — \"My reminders\"\n"
                "• **Contacts** — \"Show contacts\"\n"
                "• **Insights** — \"CRM summary\""
            ),
            "items": None,
            "links": [],
            "type": "text",
        }

    except Exception as exc:
        logger.error("[Zia] query failed: %s", exc)
        return {
            "message": "I ran into an issue fetching that data. Please try again.",
            "items": None,
            "links": [],
            "type": "text",
        }
