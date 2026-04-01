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
from app.services import groq_service as groq_svc
from app.services.action_handler import execute_action
from app.services.memory_service import get_history, add_turn, clear_history as _clear_history, get_state, set_state

logger = logging.getLogger(__name__)

# Commands that explicitly reset the conversation
_CLEAR_PHRASES = {"clear", "clear chat", "reset", "start over", "forget", "new conversation"}


async def route_query(query: str, db: Session, user: Any) -> Dict:
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

        # ── Session State Handling (Multi-step Actions) ──────────────────
        state = get_state(user_id)
        
        # Scenario: User is providing details for a pending lead creation
        if state.get("pending_action") == "create_lead":
            if query.strip().lower() in ["cancel", "stop", "exit", "nevermind"]:
                set_state(user_id, {})
                return {"message": "Okay, I've cancelled the lead creation. How else can I help?", "items": None, "links": [], "type": "text"}
                
            # Attempt to parse details (expecting: "First Last, email, company")
            parts = [p.strip() for p in query.split(",")]
            if len(parts) >= 1:
                name_parts = parts[0].split()
                # Use slice with explicit stop to satisfy some linters
                first_name = name_parts[0] if len(name_parts) > 0 else "Unknown"
                last_name = " ".join(name_parts[1:len(name_parts)]) if len(name_parts) > 1 else "Lead"
                email = parts[1] if len(parts) > 1 else ""
                company = parts[2] if len(parts) > 2 else ""
                
                action_data = {
                    "action": "create_lead",
                    "params": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "company": company
                    }
                }
                # Clear state before executing
                set_state(user_id, {})
                result = await execute_action(action_data, db, user)
                
                reply_text = result["message"]
                _store_turn(user_id, query, reply_text)
                
                links = []
                if result.get("link"):
                    label = _action_link_label(action_data)
                    links = [{"label": label, "url": result["link"]}]
                
                return {
                    "message": reply_text,
                    "items": None,
                    "links": links,
                    "type": "action_success" if result["ok"] else "action_error",
                    "action_result": result,
                }

        # Scenario: User is providing details for a pending deal creation
        if state.get("pending_action") == "create_deal":
            parts = [p.strip() for p in query.split(",")]
            name = parts[0] if len(parts) > 0 else "New Deal"
            amount_str = parts[1] if len(parts) > 1 else "0"
            # Clean amount string
            amount = 0
            try:
                amount = float(amount_str.replace("$", "").replace(",", "").strip())
            except ValueError:
                pass

            action_data = {
                "action": "create_deal",
                "params": {
                    "name": name,
                    "amount": amount
                }
            }
            set_state(user_id, {})
            result = await execute_action(action_data, db, user)
            reply_text = result["message"]
            _store_turn(user_id, query, reply_text)
            
            links = []
            if result.get("link"):
                label = _action_link_label(action_data)
                links = [{"label": label, "url": result["link"]}]
            
            return {
                "message": reply_text,
                "items": None,
                "links": links,
                "type": "action_success" if result["ok"] else "action_error",
                "action_result": result,
            }

        # ── Keyword Bypass (Action Intent) ──────────────────────────────
        low_query = query.strip().lower()
        
        # Create Lead Bypass
        if any(kw in low_query for kw in ["create lead", "add lead", "new lead", "create a lead"]):
            set_state(user_id, {"pending_action": "create_lead"})
            reply = "I'll help you create a lead! Please provide the **Name, Email, and Company** (separated by commas if possible)."
            return {"message": reply, "items": None, "links": [], "type": "text"}
        
        # Create Deal Bypass
        if any(kw in low_query for kw in ["create deal", "add deal", "new deal", "create a deal"]):
            set_state(user_id, {"pending_action": "create_deal"})
            reply = "I'll help you create a deal! Please provide the **Deal Name and Amount** (e.g., 'Big Project, 5000')."
            return {"message": reply, "items": None, "links": [], "type": "text"}

        # ── Intent detection — for everything else, use LLM ──────────────────
        intent = groq_svc.classify_query(query)
        logger.debug("[router] query=%r intent=%s user=%s", query, intent, user_id)

        # ── CRM data queries — no LLM, always fresh from DB ───────────────
        if intent == "crm_query":
            result = process_assistant_query(query, db, user)
            _store_turn(user_id, query, result.get("message", ""))
            return result

        # ── Help / how-to questions — LLM with memory context ─────────────
        if intent == "help_query":
            history = get_history(user_id)
            answer = groq_svc.generate_help_response(query, history)
            if not answer:
                return {"message": "AI service is currently unavailable, using basic assistant. Ask me specifically about leads or deals.", "items": None, "links": [], "type": "text"}
            _store_turn(user_id, query, answer)
            return {"message": answer, "items": None, "links": [], "type": "text"}

        # ── CRM actions (create / update) via LLM extraction ──────────────
        if intent == "action_query":
            action_data = groq_svc.extract_action(query)
            if not action_data:
                return {"message": "AI service is currently unavailable, using basic assistant. Please try a different query.", "items": None, "links": [], "type": "text"}

            result = await execute_action(action_data, db, user)
            reply_text = result["message"]
            _store_turn(user_id, query, reply_text)

            links = []
            if result.get("link") and result["ok"]:
                label = _action_link_label(action_data)
                links = [{"label": label, "url": result["link"]}]
            
            return {
                "message": reply_text,
                "items": None,
                "links": links,
                "type": "action_success" if result["ok"] else "action_error",
                "action_result": result,
            }

        # ── General / ambiguous — LLM with memory context ─────────────────
        history = get_history(user_id)
        answer = groq_svc.generate_help_response(query, history)
        if not answer:
             return {"message": "AI service is currently unavailable, using basic assistant.", "items": None, "links": [], "type": "text"}

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
