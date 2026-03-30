"""
Memory Service — per-user short-term conversation memory for Zia.

Stores the last MAX_TURNS exchanges (user + assistant pairs) in a plain dict.
No external dependencies, no DB — ephemeral by design (resets on server restart).

Public API:
  get_history(user_id)                      → list of Anthropic-format message dicts
  add_turn(user_id, user_msg, bot_msg)      → None
  clear_history(user_id)                    → None
  prune_expired()                           → None  (call from a background task if desired)
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_TURNS   = 10      # each turn = 1 user msg + 1 assistant msg  → 20 messages total
SESSION_TTL = 3600    # seconds; idle sessions are evicted on next access or prune call

# ── Internal store ────────────────────────────────────────────────────────────
# Shape: { user_id: {"messages": [...], "last_active": float} }
_store: Dict[Any, Dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_expired(entry: Dict) -> bool:
    return time.time() - entry.get("last_active", 0) > SESSION_TTL


# ── Public functions ──────────────────────────────────────────────────────────

def get_history(user_id: Any) -> List[Dict[str, str]]:
    """
    Return the full message list for this user in Anthropic messages format:
      [{"role": "user"|"assistant", "content": str}, ...]

    Returns an empty list if no history exists or the session has expired.
    Never raises.
    """
    try:
        entry = _store.get(user_id)
        if not entry:
            return []
        if _is_expired(entry):
            _store.pop(user_id, None)
            return []
        return list(entry["messages"])   # shallow copy — safe to mutate by caller
    except Exception as exc:
        logger.warning("[memory] get_history error: %s", exc)
        return []


def add_turn(user_id: Any, user_message: str, assistant_message: str) -> None:
    """
    Append one conversational turn (user message + assistant reply) to the user's
    history.  Evicts the oldest turn when MAX_TURNS is exceeded.
    Never raises.
    """
    try:
        if user_id not in _store:
            _store[user_id] = {"messages": [], "last_active": time.time()}

        entry = _store[user_id]
        entry["messages"].extend([
            {"role": "user",      "content": str(user_message)},
            {"role": "assistant", "content": str(assistant_message)},
        ])
        entry["last_active"] = time.time()

        # Trim to the most recent MAX_TURNS turns (2 messages per turn)
        max_msgs = MAX_TURNS * 2
        if len(entry["messages"]) > max_msgs:
            entry["messages"] = entry["messages"][-max_msgs:]

    except Exception as exc:
        logger.warning("[memory] add_turn error: %s", exc)


def clear_history(user_id: Any) -> None:
    """Remove all conversation history for this user. Never raises."""
    try:
        _store.pop(user_id, None)
        logger.debug("[memory] cleared history for user %s", user_id)
    except Exception:
        pass


def prune_expired() -> None:
    """
    Evict sessions that have been idle longer than SESSION_TTL.
    Call this from a background task or a startup event if desired.
    Never raises.
    """
    try:
        expired = [uid for uid, e in list(_store.items()) if _is_expired(e)]
        for uid in expired:
            _store.pop(uid, None)
        if expired:
            logger.debug("[memory] pruned %d expired sessions", len(expired))
    except Exception as exc:
        logger.warning("[memory] prune_expired error: %s", exc)
