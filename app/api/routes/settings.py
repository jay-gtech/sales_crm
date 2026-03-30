"""
Settings routes.

GET  /settings                — Profile page (any authenticated user)
GET  /settings/preferences    — Preferences page (any authenticated user)
GET  /settings/roles          — Role & user management (admin only)
POST /settings/profile        — Update own display name
POST /settings/roles/assign   — Assign role to a user (admin only)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request

logger = logging.getLogger(__name__)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import VALID_ROLES
from app.services.settings_service import (
    get_all_users,
    update_profile,
    update_user_role,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_ROLE_LABELS = {
    "admin":     "Admin",
    "manager":   "Manager",
    "sales_rep": "Sales Rep",
}


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    saved: Optional[str] = None,
    user=Depends(get_current_user),
):
    return templates.TemplateResponse("settings.html", {
        "request":     request,
        "title":       "Settings",
        "user":        user,
        "saved":       saved == "1",
    })


@router.get("/settings/preferences", response_class=HTMLResponse)
async def preferences_page(
    request: Request,
    user=Depends(get_current_user),
):
    return templates.TemplateResponse("settings_preferences.html", {
        "request": request,
        "title":   "Settings",
        "user":    user,
    })


@router.post("/settings/profile")
async def update_profile_post(
    request:   Request,
    full_name: str = Form(""),
    db:        Session = Depends(get_db),
    user=Depends(get_current_user),
):
    update_profile(db, user.id, full_name)
    return RedirectResponse("/settings?saved=1", status_code=303)


# ── Role management (admin only) ──────────────────────────────────────────────

@router.get("/settings/roles", response_class=HTMLResponse)
async def roles_page(
    request: Request,
    updated: Optional[str] = None,
    error:   Optional[str] = None,
    db:      Session = Depends(get_db),
    admin=Depends(require_admin),
):
    users = get_all_users(db)
    return templates.TemplateResponse("settings_roles.html", {
        "request":     request,
        "title":       "Settings",
        "user":        admin,
        "users":       users,
        "roles":       VALID_ROLES,
        "role_labels": _ROLE_LABELS,
        "updated":     updated == "1",
        "error":       error or None,
    })


@router.post("/settings/roles/assign")
async def assign_role_post(
    request:    Request,
    user_id:    int           = Form(...),
    role:       str           = Form(...),
    manager_id: Optional[str] = Form(None),   # str to safely accept empty string
    db:         Session       = Depends(get_db),
    admin=Depends(require_admin),
):
    # Convert empty string → None safely; Pydantic raises 422 if typed as int and "" submitted
    manager_id_int: Optional[int] = int(manager_id) if manager_id and manager_id.strip() else None
    logger.info("[settings/assign] user_id=%s role=%s manager_id=%r", user_id, role, manager_id_int)
    ok, msg = update_user_role(db, user_id, role, manager_id_int, admin.id)
    if ok:
        return RedirectResponse("/settings/roles?updated=1", status_code=303)
    # Re-render with error
    users = get_all_users(db)
    return templates.TemplateResponse("settings_roles.html", {
        "request":     request,
        "title":       "Settings",
        "user":        admin,
        "users":       users,
        "roles":       VALID_ROLES,
        "role_labels": _ROLE_LABELS,
        "updated":     False,
        "error":       msg,
    }, status_code=400)
