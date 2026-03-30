"""
Settings Service — user profile and role management.

All writes go through this service so validation is centralised.
Never modifies auth logic, passwords, or unrelated CRM data.
Never raises on lookup failures — returns None or [] instead.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User, VALID_ROLES

logger = logging.getLogger(__name__)


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_users(db: Session) -> List[User]:
    """Return all active users ordered by id."""
    try:
        return db.query(User).filter(User.is_active == True).order_by(User.id).all()
    except Exception as exc:
        logger.error("[settings] get_all_users failed: %s", exc)
        return []


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    try:
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except Exception as exc:
        logger.error("[settings] get_user_by_id failed: %s", exc)
        return None


# ── Write ─────────────────────────────────────────────────────────────────────

def update_profile(db: Session, user_id: int, full_name: str) -> Optional[User]:
    """Update display name for any authenticated user."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        user.full_name = (full_name or "").strip() or None
        db.commit()
        db.refresh(user)
        return user
    except Exception as exc:
        logger.error("[settings] update_profile failed: %s", exc)
        db.rollback()
        return None


def _has_circular_hierarchy(db: Session, user_id: int, proposed_manager_id: int) -> bool:
    """
    Detect A→B→A circular chains.
    Walk up from proposed_manager_id; if we reach user_id the chain is circular.
    Returns False (safe) on any exception.
    """
    try:
        visited: set = set()
        current_id: Optional[int] = proposed_manager_id
        while current_id is not None:
            if current_id == user_id:
                return True          # circular
            if current_id in visited:
                break                # prevent infinite loop on corrupt data
            visited.add(current_id)
            mgr = db.query(User).filter(User.id == current_id).first()
            current_id = mgr.manager_id if mgr else None
        return False
    except Exception:
        return False                 # fail open — let the rest of validation decide


def _count_admins(db: Session) -> int:
    """Count active admin users. Returns 999 on error (fail open)."""
    try:
        return db.query(User).filter(User.role == "admin", User.is_active == True).count()
    except Exception:
        return 999


def update_user_role(
    db: Session,
    target_user_id: int,
    role: str,
    manager_id: Optional[int],
    acting_admin_id: int,
) -> tuple[bool, str]:
    """
    Assign a role (and optional manager) to a user.
    Returns (success: bool, message: str).

    Guards (in order):
    1. Role must be in VALID_ROLES
    2. Cannot demote yourself (prevents self-lockout)
    3. Cannot remove the last admin
    4. Circular hierarchy check
    5. manager_id must point to an existing active user (or None)
    6. Cannot self-assign as manager
    """
    try:
        if role not in VALID_ROLES:
            return False, f"Invalid role '{role}'. Choose: {', '.join(VALID_ROLES)}."

        if target_user_id == acting_admin_id and role != "admin":
            return False, "You cannot change your own admin role."

        target = db.query(User).filter(User.id == target_user_id, User.is_active == True).first()
        if not target:
            return False, "User not found."

        # Guard: last admin
        if target.role == "admin" and role != "admin":
            if _count_admins(db) <= 1:
                return False, (
                    "Cannot remove the last admin. "
                    "Promote another user to admin first."
                )

        # Validate manager assignment
        resolved_manager_id: Optional[int] = None
        if manager_id:
            if manager_id == target_user_id:
                return False, "A user cannot be their own manager."
            mgr = db.query(User).filter(User.id == manager_id, User.is_active == True).first()
            if not mgr:
                return False, "Selected manager does not exist."
            # Guard: circular hierarchy
            if _has_circular_hierarchy(db, target_user_id, manager_id):
                return False, (
                    f"Circular hierarchy detected: assigning {mgr.display_name} as manager "
                    "would create a reporting loop."
                )
            resolved_manager_id = manager_id

        target.role       = role
        target.manager_id = resolved_manager_id
        db.commit()
        db.refresh(target)
        logger.info(
            "[settings] admin %s set user %s role=%s manager=%s",
            acting_admin_id, target_user_id, role, resolved_manager_id,
        )
        return True, f"Role updated to '{target.role_label}' for {target.display_name}."

    except Exception as exc:
        logger.error("[settings] update_user_role failed: %s", exc)
        db.rollback()
        return False, "An error occurred while updating the role. Please try again."
