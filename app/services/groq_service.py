"""
Groq Service — ZIA assistant integration.

Provides mirror functionality to openai_service.py but uses Groq.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

def _client():
    """Return a Groq client, or None if unavailable."""
    try:
        import groq  # optional dependency
        if not settings.GROQ_API_KEY:
            return None
        return groq.Groq(api_key=settings.GROQ_API_KEY)
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.warning("[Groq] could not create client: %s", exc)
        return None

def _strip_fences(text: str) -> str:
    """Remove markdown code fences so json.loads works cleanly."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

_CLASSIFY_SYSTEM = """\
You are ZIA, an AI assistant for a Sales CRM system.
Classify CRM assistant queries into exactly one of four categories.
Reply with ONLY a single JSON object — no prose, no explanation.

Categories:
  "crm_query"    — user wants data from the CRM (leads, deals, activities, reminders, contacts, insights)
  "help_query"   — user asks how something works or needs guidance
  "action_query" — user wants to create or update a record (create lead, add reminder, create deal)
  "general"      — none of the above

Output format (exactly):
{"intent": "<category>"}
"""

def classify_query(text: str) -> Optional[str]:
    client = _client()
    if not client: return None
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": text}
            ],
            max_tokens=64,
            temperature=0,
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        intent = data.get("intent")
        if intent in ("crm_query", "help_query", "action_query", "general"):
            return intent
    except Exception as exc:
        logger.warning("[Groq] classify_query failed: %s", exc)
    return None

_HELP_SYSTEM = """\
You are ZIA, an AI assistant for a Sales CRM system.
Help users with leads, contacts, deals, pipeline, reports, and CRM usage.

Rules:
- Provide clear, step-by-step guidance for actions
- Keep answers short, accurate, and relevant
- Do not generate features not present in CRM
- If unsure, guide user safely
- Be professional and helpful
- Focus on CRM usage: managing leads, deals, contacts, activities, and reminders.
- Do NOT use markdown headers. Use plain text or simple bullet points.
"""

def generate_help_response(
    text: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    client = _client()
    if not client: return None
    try:
        messages = [{"role": "system", "content": _HELP_SYSTEM}]
        if history:
            for turn in history:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append({"role": "user", "content": text})

        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            max_tokens=400,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("[Groq] generate_help_response failed: %s", exc)
    return None

_ACTION_SYSTEM = """\
You are ZIA, an AI assistant for a Sales CRM system.
Extract a structured action from a CRM assistant request.
Reply with ONLY a JSON object — no prose, no explanation.

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
    client = _client()
    if not client: return None
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _ACTION_SYSTEM},
                {"role": "user", "content": text}
            ],
            max_tokens=256,
            temperature=0,
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        if data.get("action"):
            return data
    except Exception as exc:
        logger.warning("[Groq] extract_action failed: %s", exc)
    return None
