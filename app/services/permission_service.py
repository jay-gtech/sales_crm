"""
Permission Service — RBAC permission matrix for the CRM.

Design principles:
- Fail-safe: any exception in a check → return True (allow). Never crash the CRM.
- No DB writes — read-only helper used by routes and templates.
- Modular: imported wherever permission logic is needed.

Permission scopes:
  "all"  → user sees / edits every record regardless of owner
  "team" → user sees / edits own records + direct reports' records
  "own"  → user sees / edits only their own records
  True   → blanket allow
  False  → blanket deny

Usage:
  from app.services import permission_service as perm

  # Can this user delete leads?
  if not perm.can_delete(user, "leads"):
      return redirect("/leads")

  # Filter a list to what this user may see
  leads = perm.filter_by_visibility(leads, user, db, owner_attr="owner_id")
"""

import logging
from typing import Any, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Permission matrix ─────────────────────────────────────────────────────────

MATRIX = {
    "admin": {
        "leads":      {"view": "all",  "create": True, "edit": "all",  "delete": True},
        "deals":      {"view": "all",  "create": True, "edit": "all",  "delete": True},
        "activities": {"view": "all",  "create": True, "edit": "all",  "delete": True},
        "contacts":   {"view": "all",  "create": True, "edit": "all",  "delete": True},
        "settings":   {"view": "all",  "create": True, "edit": "all",  "delete": True},
    },
    "manager": {
        "leads":      {"view": "team", "create": True, "edit": "team", "delete": False},
        "deals":      {"view": "team", "create": True, "edit": "team", "delete": False},
        "activities": {"view": "team", "create": True, "edit": "team", "delete": False},
        "contacts":   {"view": "all",  "create": True, "edit": "all",  "delete": False},
        "settings":   {"view": "own",  "create": False, "edit": "own", "delete": False},
    },
    "sales_rep": {
        "leads":      {"view": "own",  "create": True, "edit": "own",  "delete": False},
        "deals":      {"view": "own",  "create": True, "edit": "own",  "delete": False},
        "activities": {"view": "own",  "create": True, "edit": "own",  "delete": False},
        "contacts":   {"view": "all",  "create": True, "edit": "own",  "delete": False},
        "settings":   {"view": "own",  "create": False, "edit": "own", "delete": False},
    },
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _role(user: Any) -> str:
    """Resolve role string, defaulting to 'sales_rep' for unknown/missing."""
    r = getattr(user, "role", None) or "sales_rep"
    return r if r in MATRIX else "sales_rep"


def _team_ids(user: Any, db: Session) -> List[int]:
    """Return [user.id] + ids of direct reports. Never raises."""
    try:
        from app.models.user import User
        rows = (
            db.query(User.id)
            .filter(User.manager_id == user.id, User.is_active == True)
            .all()
        )
        return [user.id] + [r[0] for r in rows]
    except Exception as exc:
        logger.warning("[perm] _team_ids error: %s", exc)
        return [user.id]


# ── Public API ────────────────────────────────────────────────────────────────

def has_permission(
    user: Any,
    action: str,
    resource: str,
    resource_owner_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> bool:
    """
    Check if `user` may perform `action` on `resource`.

    action   : "view" | "create" | "edit" | "delete"
    resource : "leads" | "deals" | "activities" | "contacts" | "settings"
    resource_owner_id : owner_id of the specific record (None → assume allowed)

    Returns True if allowed, False if denied.
    Fails OPEN (returns True) on any unexpected error so the CRM never locks up.
    """
    try:
        scope = MATRIX.get(_role(user), {}).get(resource, {}).get(action)

        if scope is None:
            return True          # unknown resource/action — fail open

        if scope is False:
            return False

        if scope is True or scope == "all":
            return True

        if resource_owner_id is None:
            return True          # no ownership context — fail open

        if scope == "own":
            return resource_owner_id == getattr(user, "id", None)

        if scope == "team":
            uid = getattr(user, "id", None)
            if resource_owner_id == uid:
                return True
            if db is None:
                return True      # no DB context — fail open
            try:
                from app.models.user import User
                owner = db.query(User).filter(User.id == resource_owner_id).first()
                return owner is not None and owner.manager_id == uid
            except Exception:
                return True      # fail open

        return True              # unknown scope — fail open

    except Exception as exc:
        logger.warning("[perm] has_permission error (failing open): %s", exc)
        return True


def can_delete(user: Any, resource: str) -> bool:
    """
    Quick check: may this user delete records of `resource`?
    Fails CLOSED on delete (safer than failing open).
    """
    try:
        return bool(MATRIX.get(_role(user), {}).get(resource, {}).get("delete", False))
    except Exception as exc:
        logger.warning("[perm] can_delete error (failing closed): %s", exc)
        return False


def get_visible_owner_ids(user: Any, db: Session) -> Optional[List[int]]:
    """
    Return the list of owner_ids this user may see for records.
    Returns None if the user may see ALL records (no filter needed).
    Never raises — returns None (all) on any error to keep the CRM working.
    """
    try:
        scope = MATRIX.get(_role(user), {}).get("leads", {}).get("view", "own")

        if scope == "all":
            return None                    # no filter

        if scope == "own":
            return [getattr(user, "id", 0)]

        if scope == "team":
            return _team_ids(user, db)

        return [getattr(user, "id", 0)]    # fallback: own

    except Exception as exc:
        logger.warning("[perm] get_visible_owner_ids error (failing open): %s", exc)
        return None                        # fail open — show all


def filter_by_visibility(
    records: List[Any],
    user: Any,
    db: Session,
    owner_attr: str = "owner_id",
) -> List[Any]:
    """
    Filter a list of ORM records to only those visible to `user`.
    Records missing `owner_attr` (e.g. unlinked activities) are always included.
    Never raises — returns the original list on any error.
    """
    try:
        visible = get_visible_owner_ids(user, db)
        if visible is None:
            return records              # admin / all-scope

        filtered = []
        for rec in records:
            oid = getattr(rec, owner_attr, None)
            if oid is None or oid in visible:
                filtered.append(rec)
        return filtered

    except Exception as exc:
        logger.warning("[perm] filter_by_visibility error (returning all): %s", exc)
        return records
