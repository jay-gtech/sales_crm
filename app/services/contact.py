"""
Contact service layer — clean business logic, thin routes.
Accepts raw dicts so image paths can be pre-processed before insertion.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.contact import Contact

logger = logging.getLogger(__name__)


# ── Read ─────────────────────────────────────────────────────────────────────

def get_contacts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> List[Contact]:
    """Return all contacts ordered newest first."""
    return (
        db.query(Contact)
        .order_by(Contact.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_contact(db: Session, contact_id: int) -> Optional[Contact]:
    """Return a single contact by primary key, or None."""
    return db.query(Contact).filter(Contact.id == contact_id).first()


def get_contact_by_email(db: Session, email: str) -> Optional[Contact]:
    """Look up a contact by primary email address."""
    return db.query(Contact).filter(Contact.email == email).first()


def search_contacts(
    db: Session,
    query: str,
    skip: int = 0,
    limit: int = 50,
) -> List[Contact]:
    """Full-name / email search (case-insensitive LIKE)."""
    like = f"%{query}%"
    return (
        db.query(Contact)
        .filter(
            Contact.last_name.ilike(like)
            | Contact.first_name.ilike(like)
            | Contact.email.ilike(like)
        )
        .order_by(Contact.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ── Write ────────────────────────────────────────────────────────────────────

def create_contact(db: Session, data: Dict[str, Any]) -> Contact:
    """
    Create a new Contact from a plain dict.
    Accepts raw form data (after image path is resolved by the route).
    Only keys that exist as model columns are passed to the ORM.
    """
    # Safety: strip any keys that are not columns on the model to avoid
    # unexpected keyword argument errors if the form ever sends extras.
    valid_columns = {c.name for c in Contact.__table__.columns}
    clean_data = {k: v for k, v in data.items() if k in valid_columns}

    db_contact = Contact(**clean_data)
    try:
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create contact: %s", exc)
        raise
    return db_contact


def update_contact(
    db: Session,
    contact_id: int,
    data: Dict[str, Any],
) -> Optional[Contact]:
    """Update an existing contact with the supplied dict of changes."""
    contact = get_contact(db, contact_id)
    if not contact:
        return None

    valid_columns = {c.name for c in Contact.__table__.columns}
    for key, value in data.items():
        if key in valid_columns and key != "id":
            setattr(contact, key, value)
    try:
        db.commit()
        db.refresh(contact)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update contact %s: %s", contact_id, exc)
        raise
    return contact


def delete_contact(db: Session, contact_id: int) -> bool:
    """Delete a contact by ID. Returns True if deleted, False if not found."""
    contact = get_contact(db, contact_id)
    if not contact:
        return False
    try:
        db.delete(contact)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete contact %s: %s", contact_id, exc)
        raise
    return True
