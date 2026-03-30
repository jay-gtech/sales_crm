import os
import time
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.core.config import settings
import app.db.base  # noqa: F401 — registers ALL models with SQLAlchemy before any route imports them
from app.api.routes import auth, leads, contacts, deals, activities, ai, public, reminders, communication, ai_assistant
from app.api.routes import settings as settings_routes
from app.api.endpoints import meeting, chatbot
from app.api.deps import get_current_user

app = FastAPI(title=settings.PROJECT_NAME)

# ── Demo Mode middleware ────────────────────────────────────────────────────
# When DEMO_MODE=True, every request is printed to the console.
# This does NOT affect any business logic — purely observational.
if settings.DEMO_MODE:
    @app.middleware("http")
    async def demo_mode_logger(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        print(
            f"[DEMO] {request.method} {request.url.path}"
            f" -> {response.status_code} ({duration_ms}ms)"
        )
        return response

@app.on_event("startup")
def migrate_leads_phone_constraint():
    """
    Remove the erroneous UNIQUE constraint on leads.phone.
    SQLite cannot ALTER TABLE DROP CONSTRAINT, so we inspect sqlite_master for
    any unique index covering phone and drop it, then recreate as a plain index.
    Safe to run repeatedly — idempotent.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        # Find all indexes on the leads table
        rows = db.execute(text(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND tbl_name='leads'"
        )).fetchall()

        for name, sql in rows:
            if sql and "phone" in sql.lower() and "unique" in sql.upper():
                db.execute(text(f"DROP INDEX IF EXISTS \"{name}\""))
                db.commit()
                print(f"[migrate] Dropped unique index '{name}' from leads.phone")

        # Ensure a plain (non-unique) index still exists for query performance
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_leads_phone_plain ON leads (phone)"
        ))
        db.commit()
    except Exception as exc:
        print(f"[migrate] leads.phone constraint migration failed: {exc}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def migrate_email_log_table():
    """Create email_logs table if it doesn't exist (idempotent)."""
    from app.db.session import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                to_email     VARCHAR(320) NOT NULL,
                subject      VARCHAR(998) NOT NULL,
                body         TEXT,
                status       VARCHAR(10)  NOT NULL DEFAULT 'sent',
                related_type VARCHAR(20),
                related_id   INTEGER,
                sent_by_id   INTEGER,
                created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()
    except Exception as exc:
        print(f"[migrate] email_logs table migration failed: {exc}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def migrate_user_table():
    """
    Safely add new columns to the users table if they don't exist yet.
    SQLite supports ALTER TABLE ... ADD COLUMN but not DROP/MODIFY, so
    we attempt each addition and swallow the 'duplicate column' error.
    Also ensures the very first user (lowest id) has role='admin'.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        new_columns = [
            "ALTER TABLE users ADD COLUMN full_name VARCHAR",
            "ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'sales_rep'",
            "ALTER TABLE users ADD COLUMN manager_id INTEGER REFERENCES users(id)",
        ]
        for sql in new_columns:
            try:
                db.execute(text(sql))
                db.commit()
            except Exception:
                db.rollback()   # column already exists — safe to ignore

        # Promote the first registered user to admin automatically
        db.execute(text(
            "UPDATE users SET role = 'admin' "
            "WHERE id = (SELECT MIN(id) FROM users) "
            "AND (role IS NULL OR role = 'sales_rep')"
        ))
        db.commit()
    except Exception as exc:
        print(f"[migrate] user table migration failed: {exc}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def print_startup_banner():
    mode = "DEMO MODE  (set DEMO_MODE=False in config.py for production)" if settings.DEMO_MODE else "PRODUCTION MODE"
    print(f"\n{'='*60}")
    print(f"  {settings.PROJECT_NAME}  —  {mode}")
    print(f"  DB: {settings.SQLALCHEMY_DATABASE_URI}")
    print(f"{'='*60}\n")

@app.on_event("startup")
def seed_sample_leads():
    from app.db.session import SessionLocal
    from app.models.lead import Lead
    db = SessionLocal()
    try:
        if db.query(Lead).count() == 0:
            samples = [
                Lead(first_name="John",  last_name="Doe",     email="john.doe@example.com",    phone="555-0101", company="Acme Corp",    status="New",         lead_score=20),
                Lead(first_name="Alice", last_name="Smith",   email="alice.smith@example.com", phone="555-0102", company="TechStart",   status="Contacted",   lead_score=35),
                Lead(first_name="Raj",   last_name="Kumar",   email="raj.kumar@example.com",   phone="555-0103", company="GlobalBiz",   status="Qualified",   lead_score=60),
                Lead(first_name="Maria", last_name="Garcia",  email="maria.garcia@example.com",phone="555-0104", company="RetailPlus",  status="Proposal Sent", lead_score=75),
                Lead(first_name="Tom",   last_name="Wilson",  email="tom.wilson@example.com",  phone="555-0105", company="SalesForce",  status="Negotiation", lead_score=85),
            ]
            db.add_all(samples)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

@app.on_event("startup")
def seed_sample_activities():
    from app.db.session import SessionLocal
    from app.models.activity import Activity
    from app.models.lead import Lead
    from app.models.deal import Deal
    db = SessionLocal()
    try:
        if db.query(Activity).count() == 0:
            leads = db.query(Lead).limit(3).all()
            deals = db.query(Deal).limit(2).all()
            samples = []
            if leads:
                samples.extend([
                    Activity(
                        title="Initial qualification call",
                        activity_type="Call",
                        status="completed",
                        description=f"Called {leads[0].first_name} to discuss requirements and budget.",
                        lead_id=leads[0].id,
                    ),
                    Activity(
                        title="Follow-up email sent",
                        activity_type="Email",
                        status="completed",
                        description="Sent product overview and pricing deck.",
                        lead_id=leads[1].id if len(leads) > 1 else leads[0].id,
                    ),
                    Activity(
                        title="Discovery meeting scheduled",
                        activity_type="Meeting",
                        status="pending",
                        description="Scheduled for next week to review specific needs.",
                        lead_id=leads[2].id if len(leads) > 2 else leads[0].id,
                    ),
                ])
            if deals:
                samples.append(Activity(
                    title="Contract review call",
                    activity_type="Call",
                    status="pending",
                    description="Schedule final contract review with legal team.",
                    deal_id=deals[0].id,
                ))
                if len(deals) > 1:
                    samples.append(Activity(
                        title="Proposal submitted",
                        activity_type="Email",
                        status="completed",
                        description="Sent detailed proposal with timeline and deliverables.",
                        deal_id=deals[1].id,
                    ))
            if samples:
                db.add_all(samples)
                db.commit()
    except Exception as e:
        print(f"[seed] activities seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Jinja2 templates — expose demo_mode as a global so every template can use it
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["demo_mode"] = settings.DEMO_MODE

# Include routers
app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(contacts.router)
app.include_router(deals.router)
app.include_router(activities.router)
app.include_router(ai.router)
app.include_router(meeting.router)
app.include_router(chatbot.router)
app.include_router(public.router)
app.include_router(reminders.router)
app.include_router(communication.router)
app.include_router(ai_assistant.router)
app.include_router(settings_routes.router)

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.dashboard_service import get_dashboard_data, get_report_data

@app.exception_handler(401)
async def custom_401_handler(request: Request, __):
    return RedirectResponse("/login")

@app.exception_handler(403)
async def custom_403_handler(request: Request, __):
    """Admin-only pages redirect non-admins to home instead of showing a raw 403."""
    return RedirectResponse("/")

@app.get("/dashboard")
async def dashboard_view(request: Request, db: Session = Depends(get_db), user = Depends(get_current_user)):
    report_data = get_report_data(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Reports",
        "user": user,
        "data": report_data,
    })

@app.get("/help")
async def help_page(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("help.html", {
        "request": request, "title": "Help & Onboarding", "user": user
    })

@app.get("/sop")
async def sop_page(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("sop.html", {
        "request": request, "title": "SOP", "user": user
    })

@app.get("/")
async def read_root(request: Request, db: Session = Depends(get_db), user = Depends(get_current_user)):
    dashboard_data = get_dashboard_data(db, user.id)
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "title": "Dashboard", 
        "user": user,
        "data": dashboard_data
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
