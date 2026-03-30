"""
AI Router — classifies a user query and routes it to the right handler.

Query types:
  crm_query    → existing ai_assistant_service (fast, DB-backed, no LLM needed)
  help_query   → LLM answer with conversation memory context
  action_query → LLM-extracted action → action_handler
  general      → LLM answer with memory context, fallback to static message

Memory is keyed by user.id — each user has an independent conversation history
that persists for the duration of the server process (SESSION_TTL = 1 hour idle).

Returns the same shape as ai_assistant_service:
  { message, items, links, type, action_result? }

Never raises.
"""
import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.services.ai_assistant_service import process_assistant_query
from app.services.llm_service import classify_query, extract_action, generate_help_response
from app.services.action_handler import execute_action
from app.services.memory_service import get_history, add_turn, clear_history as _clear_history

logger = logging.getLogger(__name__)

# Commands that explicitly reset the conversation
_CLEAR_PHRASES = {"clear", "clear chat", "reset", "start over", "forget", "new conversation"}


def route_query(query: str, db: Session, user: Any) -> Dict:
    """
    Main entry point called by the API endpoint.
    Classifies the query and delegates to the appropriate handler.
    Automatically stores each turn in the per-user memory.
    Never raises.
    """
    user_id = getattr(user, "id", None)

    try:
        # ── Explicit memory reset ──────────────────────────────────────────
        if query.strip().lower() in _CLEAR_PHRASES:
            _clear_history(user_id)
            reply = "Conversation cleared. How can I help you?"
            return {"message": reply, "items": None, "links": [], "type": "text"}

        intent = classify_query(query)
        logger.debug("[router] query=%r intent=%s user=%s", query, intent, user_id)

        # ── CRM data queries — no LLM, always fresh from DB ───────────────
        if intent == "crm_query":
            result = process_assistant_query(query, db, user)
            # Store a compact summary in memory so follow-up questions have context
            _store_turn(user_id, query, result.get("message", ""))
            return result

        # ── Help / how-to questions — LLM with memory context ─────────────
        if intent == "help_query":
            history = get_history(user_id)
            answer  = generate_help_response(query, history)
            _store_turn(user_id, query, answer)
            return {"message": answer, "items": None, "links": [], "type": "text"}

        # ── CRM actions (create / update) ──────────────────────────────────
        if intent == "action_query":
            action_data = extract_action(query)
            result      = execute_action(action_data, db, user)

            # Build reply text and store in memory
            reply_text = result["message"]
            _store_turn(user_id, query, reply_text)

            if result["ok"]:
                links = []
                if result.get("link"):
                    label = _action_link_label(action_data)
                    links = [{"label": label, "url": result["link"]}]
                return {
                    "message": reply_text,
                    "items": None,
                    "links": links,
                    "type": "action_success",
                    "action_result": result,
                }
            else:
                return {
                    "message": reply_text,
                    "items": None,
                    "links": [],
                    "type": "action_error",
                    "action_result": result,
                }

        # ── General / ambiguous — LLM with memory context, static fallback ─
        history = get_history(user_id)
        answer  = generate_help_response(query, history)
        _store_turn(user_id, query, answer)
        return {"message": answer, "items": None, "links": [], "type": "text"}

    except Exception as exc:
        logger.error("[router] unhandled error: %s", exc)
        return {
            "message": "I ran into an issue. Please try again.",
            "items": None,
            "links": [],
            "type": "text",
        }


def _store_turn(user_id: Any, user_msg: str, assistant_msg: str) -> None:
    """Persist a conversational turn to memory, silently skipping on error."""
    try:
        if user_id is not None:
            add_turn(user_id, user_msg, assistant_msg)
    except Exception as exc:
        logger.warning("[router] could not store memory turn: %s", exc)


def _action_link_label(action_data) -> str:
    if not action_data:
        return "→ View"
    action = (action_data.get("action") or "")
    return {"create_lead": "→ View Lead", "create_deal": "→ View Deal"}.get(action, "→ View")


def _fallback() -> Dict:
    return {
        "message": (
            "I'm not sure about that. Try asking:\n\n"
            "• **Leads** — \"Show my leads\"\n"
            "• **Deals** — \"Active deals\" or \"Pipeline\"\n"
            "• **Activities** — \"Pending tasks\"\n"
            "• **Reminders** — \"My reminders\"\n"
            "• **Contacts** — \"Show contacts\"\n"
            "• **Insights** — \"CRM summary\"\n"
            "• **Actions** — \"Create a lead for John Smith\""
        ),
        "items": None,
        "links": [],
        "type": "text",
    }
