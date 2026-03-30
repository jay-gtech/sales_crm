"""
LLM Service — Claude API integration for Zia AI assistant.

Provides:
  classify_query(text) → "crm_query" | "help_query" | "action_query" | "general"
  generate_help_response(text) → str
  extract_action(text) → dict | None

Falls back gracefully if the anthropic package is not installed or the API key
is missing/invalid. Every public function returns a safe default instead of raising.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── helpers ───────────────────────────────────────────────────────────────────

def _client():
    """Return an Anthropic client, or None if unavailable."""
    try:
        import anthropic  # optional dependency
        key = settings.ANTHROPIC_API_KEY
        if not key:
            return None
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        return None
    except Exception as exc:
        logger.warning("[LLM] could not create client: %s", exc)
        return None


def _call(system: str, user: str, max_tokens: int = 512) -> Optional[str]:
    """
    Single-turn Claude call.
    Returns the text content on success, None on any failure.
    """
    client = _client()
    if client is None:
        return None
    try:
        resp = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else None
    except Exception as exc:
        logger.warning("[LLM] API call failed: %s", exc)
        return None


def _call_with_history(
    system: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 512,
) -> Optional[str]:
    """
    Multi-turn Claude call.
    `messages` is the full conversation history in Anthropic format:
      [{"role": "user"|"assistant", "content": str}, ...]
    The last element should be the current user message.
    Returns the assistant reply text, or None on failure.
    """
    client = _client()
    if client is None:
        return None
    if not messages:
        return None
    try:
        resp = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return resp.content[0].text if resp.content else None
    except Exception as exc:
        logger.warning("[LLM] API call (multi-turn) failed: %s", exc)
        return None


def _strip_fences(text: str) -> str:
    """Remove markdown code fences so json.loads works cleanly."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ── keyword-based classification (zero-cost fallback) ─────────────────────────

_ACTION_KEYWORDS = [
    "create lead", "add lead", "new lead",
    "create deal", "add deal", "new deal",
    "add reminder", "set reminder", "create reminder", "remind me",
]
_HELP_KEYWORDS = [
    "how do i", "how to", "what is", "what are", "explain",
    "can you", "tell me about", "guide", "tutorial",
]
_CRM_KEYWORDS = [
    "lead", "deal", "contact", "activity", "reminder",
    "pipeline", "revenue", "report", "dashboard",
]


def _keyword_classify(text: str) -> Optional[str]:
    lower = text.lower()
    for kw in _ACTION_KEYWORDS:
        if kw in lower:
            return "action_query"
    for kw in _HELP_KEYWORDS:
        if kw in lower:
            return "help_query"
    for kw in _CRM_KEYWORDS:
        if kw in lower:
            return "crm_query"
    return None


# ── public functions ───────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
You classify CRM assistant queries into exactly one of four categories.
Reply with ONLY a single JSON object — no prose, no markdown, no explanation.

Categories:
  "crm_query"    — user wants data from the CRM (leads, deals, activities, reminders, contacts, insights)
  "help_query"   — user asks how something works or needs guidance
  "action_query" — user wants to create or update a record (create lead, add reminder, create deal)
  "general"      — none of the above

Output format (exactly):
{"intent": "<category>"}
"""

def classify_query(text: str) -> str:
    """
    Return one of: crm_query | help_query | action_query | general.
    Uses keyword heuristic first; falls back to LLM only when ambiguous.
    Never raises.
    """
    try:
        kw = _keyword_classify(text)
        if kw:
            return kw

        raw = _call(_CLASSIFY_SYSTEM, text, max_tokens=64)
        if raw:
            data = json.loads(_strip_fences(raw))
            intent = data.get("intent", "general")
            if intent in ("crm_query", "help_query", "action_query", "general"):
                return intent
    except Exception as exc:
        logger.warning("[LLM] classify_query failed: %s", exc)
    return "general"


_HELP_SYSTEM = """\
You are Zia, the AI assistant for a sales CRM platform.
Answer the user's question clearly and concisely (3-5 sentences max).
Focus on CRM usage: managing leads, deals, contacts, activities, and reminders.
Do NOT use markdown headers. Use plain text or simple bullet points.
"""

def generate_help_response(
    text: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Return a plain-text help answer, optionally using conversation history for context.
    Falls back gracefully if LLM is unavailable.
    Never raises.
    """
    try:
        # Build message list: prior history + current user message
        messages: List[Dict[str, str]] = list(history or [])
        messages.append({"role": "user", "content": text})

        raw = _call_with_history(_HELP_SYSTEM, messages, max_tokens=400)
        if raw:
            return raw.strip()
    except Exception as exc:
        logger.warning("[LLM] generate_help_response failed: %s", exc)

    # Static fallback
    return (
        "I can help you manage leads, deals, contacts, activities, and reminders. "
        "Try asking: \"Show my leads\", \"Active deals\", \"CRM summary\", or "
        "\"Create a lead for John Smith\"."
    )


_ACTION_SYSTEM = """\
You extract a structured action from a CRM assistant request.
Reply with ONLY a JSON object — no prose, no markdown, no explanation.

Supported action types and their required/optional fields:

create_lead:
  required: first_name (str), last_name (str)
  optional: email (str), phone (str), company (str), status (str, default "New")

add_reminder:
  required: title (str), reminder_time (ISO-8601 datetime string, e.g. "2025-06-01T09:00:00")
  optional: description (str)

create_deal:
  required: name (str)
  optional: amount (float), stage (str, default "New")

Output format (exactly):
{
  "action": "<action_type>",
  "params": { ... }
}

If you cannot extract a clear action, output:
{"action": null, "params": {}}
"""

def extract_action(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a natural language request into a structured action dict.
    Returns {"action": str, "params": dict} or None on failure.
    Never raises.
    """
    try:
        raw = _call(_ACTION_SYSTEM, text, max_tokens=256)
        if not raw:
            return _keyword_extract_action(text)

        data = json.loads(_strip_fences(raw))
        if data.get("action") is None:
            return _keyword_extract_action(text)
        return data

    except Exception as exc:
        logger.warning("[LLM] extract_action failed: %s", exc)
        return _keyword_extract_action(text)


def _keyword_extract_action(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort keyword-only action extraction when LLM is unavailable.
    Handles the most common phrasings only.
    """
    lower = text.lower()

    if any(kw in lower for kw in ("create lead", "add lead", "new lead")):
        # Try to grab a name after the keyword
        m = re.search(r"(?:create lead|add lead|new lead)\s+(?:for\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.I)
        parts = m.group(1).split() if m else []
        return {
            "action": "create_lead",
            "params": {
                "first_name": parts[0] if parts else "Unknown",
                "last_name":  parts[1] if len(parts) > 1 else "Lead",
            },
        }

    if any(kw in lower for kw in ("add reminder", "set reminder", "create reminder", "remind me")):
        m = re.search(r"(?:remind(?:er)?(?:\s+me)?(?:\s+to)?|set reminder|add reminder)\s+(.+)", text, re.I)
        title = m.group(1).strip() if m else "Follow up"
        return {
            "action": "add_reminder",
            "params": {"title": title[:80]},
        }

    if any(kw in lower for kw in ("create deal", "add deal", "new deal")):
        m = re.search(r"(?:create deal|add deal|new deal)\s+(?:for\s+|called\s+|named\s+)?(.+)", text, re.I)
        name = m.group(1).strip() if m else "New Deal"
        return {
            "action": "create_deal",
            "params": {"name": name[:80]},
        }

    return None
