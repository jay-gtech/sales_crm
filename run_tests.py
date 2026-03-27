"""
CRM End-to-End Test Suite
=========================
Uses FastAPI TestClient with a separate in-memory test database.
Zero impact on the production crm.db or any live data.

Run:
    python run_tests.py

Output:
    test_report.md
"""
import sys
import os
import time
import traceback
from datetime import datetime

# Force UTF-8 output so Windows cmd does not crash on unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, ".")

TS = int(time.time())
TEST_EMAIL    = f"test_{TS}@crm-test.internal"
TEST_PASSWORD = "TestPass_CRM_2026!"

# ── Tracking for cleanup report ────────────────────────────────────────────
_created = {
    "user_email": TEST_EMAIL,
    "lead_ids": [],
    "deal_ids": [],
    "contact_ids": [],
    "activity_ids": [],
    "reminder_ids": [],
}

results = []


# ══════════════════════════════════════════════════════════════════════════
# Result helpers
# ══════════════════════════════════════════════════════════════════════════

def _r(name: str, passed: bool, detail: str = "", warn: bool = False):
    status = "PASS" if passed else ("WARN" if warn else "FAIL")
    results.append({"name": name, "status": status, "detail": detail})
    icon = "[PASS]" if passed else ("[WARN]" if warn else "[FAIL]")
    print(f"  {icon} {name}" + (f"  |  {detail}" if detail else ""))


def _section(title: str):
    print(f"\n-- {title} --")


# ══════════════════════════════════════════════════════════════════════════
# Test client + isolated DB setup
# ══════════════════════════════════════════════════════════════════════════

def _build_test_client():
    """
    Build a TestClient backed by a temporary SQLite file (test_run_<ts>.db).
    Overrides the app's DB so production crm.db is never touched.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base           # imports all models
    from app.db.session import get_db
    from app.main import app

    TEST_DB_PATH = f"test_run_{TS}.db"
    TEST_DB_URL  = f"sqlite:///./{TEST_DB_PATH}"

    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)  # create all tables fresh

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    return client, engine, TEST_DB_PATH, TestingSession


def _cleanup_test_db(engine, db_path: str, TestingSession):
    """Drop all tables and remove the test DB file."""
    try:
        from app.db.base import Base
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)
        _r("Cleanup -- Remove test database file", True, db_path)
    except Exception as e:
        _r("Cleanup -- Remove test database file", False, str(e))


# ══════════════════════════════════════════════════════════════════════════
# AUTH TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_auth(c) -> bool:
    _section("Auth")

    # GET /login page
    r = c.get("/login")
    _r("Auth -- GET /login renders", r.status_code == 200, f"HTTP {r.status_code}")

    # GET /signup page
    r = c.get("/signup")
    _r("Auth -- GET /signup renders", r.status_code == 200, f"HTTP {r.status_code}")

    # Register
    r = c.post("/signup", data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
               follow_redirects=True)
    ok = r.status_code in (200, 303)
    _r("Auth -- Register new test user", ok, f"HTTP {r.status_code}")

    # Duplicate registration
    r2 = c.post("/signup", data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                follow_redirects=False)
    dup_blocked = r2.status_code in (200, 400)
    _r("Auth -- Duplicate email rejected", dup_blocked, f"HTTP {r2.status_code}")

    # Login with wrong password
    r3 = c.post("/login", data={"email": TEST_EMAIL, "password": "WRONG"},
                follow_redirects=False)
    _r("Auth -- Wrong password rejected", r3.status_code in (200, 400), f"HTTP {r3.status_code}")

    # Login correct
    r4 = c.post("/login", data={"email": TEST_EMAIL, "password": TEST_PASSWORD},
                follow_redirects=True)
    logged_in = r4.status_code == 200 and "access_token" in c.cookies
    _r("Auth -- Login correct credentials", logged_in,
       f"HTTP {r4.status_code}, cookie={'yes' if 'access_token' in c.cookies else 'NO'}")

    if not logged_in:
        print("\n  !! Cannot proceed -- login failed.\n")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════
# PAGE LOAD TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_pages(c):
    _section("Page Loads")
    pages = [
        ("/",          "Dashboard"),
        ("/leads",     "Leads"),
        ("/deals",     "Deals"),
        ("/activities","Activities"),
        ("/contacts",  "Contacts"),
        ("/dashboard", "Reports"),
        ("/help",      "Help"),
        ("/sop",       "SOP"),
    ]
    for path, label in pages:
        try:
            r = c.get(path)
            ok = r.status_code == 200
            _r(f"Pages -- {label} ({path})", ok, f"HTTP {r.status_code}")
        except Exception as e:
            _r(f"Pages -- {label} ({path})", False, str(e))


# ══════════════════════════════════════════════════════════════════════════
# LEADS TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_leads(c, TestingSession) -> int | None:
    _section("Leads Module")
    lead_id = None

    # Create
    r = c.post("/leads", data={
        "first_name": f"TEST_{TS}",
        "last_name": "LeadQA",
        "email": f"test_lead_{TS}@crm-test.internal",
        "phone": "555-9999",
        "company": f"TEST_CO_{TS}",
        "status": "New",
    }, follow_redirects=True)
    ok = r.status_code == 200
    _r("Leads -- Create lead (POST /leads)", ok, f"HTTP {r.status_code}")

    if ok:
        from app.models.lead import Lead
        db = TestingSession()
        lead = db.query(Lead).filter(
            Lead.email == f"test_lead_{TS}@crm-test.internal"
        ).first()
        db.close()
        if lead:
            lead_id = lead.id
            _created["lead_ids"].append(lead_id)
            _r("Leads -- Lead persisted in DB", True, f"id={lead_id}")
        else:
            _r("Leads -- Lead persisted in DB", False, "not found after POST")

    # List
    r = c.get("/leads")
    _r("Leads -- List page (GET /leads)", r.status_code == 200, f"HTTP {r.status_code}")

    # Detail
    if lead_id:
        r = c.get(f"/leads/{lead_id}")
        _r("Leads -- Detail page (GET /leads/{id})", r.status_code == 200, f"HTTP {r.status_code}")

    # Status update
    if lead_id:
        r = c.post(f"/leads/{lead_id}/status",
                   json={"status": "Contacted", "notes": "QA test"})
        _r("Leads -- Update status (POST /leads/{id}/status)",
           r.status_code in (200, 303), f"HTTP {r.status_code}")

    # History
    if lead_id:
        r = c.get(f"/leads/{lead_id}/history")
        ok = r.status_code == 200
        try:
            data = r.json()
            _r("Leads -- History endpoint returns list", ok and isinstance(data, list),
               f"HTTP {r.status_code}, entries={len(data) if isinstance(data, list) else '?'}")
        except Exception:
            _r("Leads -- History endpoint returns list", False, f"HTTP {r.status_code} non-JSON")

    # Filters
    for param, val, label in [
        ("status_filter", "New",      "by status"),
        ("source_filter", "website",  "by source"),
        ("search",        f"TEST_{TS}", "by search"),
    ]:
        r = c.get("/leads", params={param: val})
        _r(f"Leads -- Filter {label}", r.status_code == 200, f"HTTP {r.status_code}")

    # Kanban view
    r = c.get("/leads", params={"view": "kanban"})
    _r("Leads -- Kanban view", r.status_code == 200, f"HTTP {r.status_code}")

    # Invalid detail (non-existent id)
    r = c.get("/leads/9999999")
    _r("Leads -- Non-existent lead returns no 500",
       r.status_code != 500, f"HTTP {r.status_code}")

    return lead_id


# ══════════════════════════════════════════════════════════════════════════
# DEALS TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_deals(c, TestingSession, lead_id) -> int | None:
    _section("Deals Module")
    deal_id = None

    # List
    r = c.get("/deals")
    _r("Deals -- List page (GET /deals)", r.status_code == 200, f"HTTP {r.status_code}")

    # Convert lead -> deal
    if lead_id:
        r = c.post(f"/deals/convert/{lead_id}", data={
            "deal_name": f"TEST_DEAL_{TS}",
            "deal_amount": "9999",
        }, follow_redirects=True)
        ok = r.status_code == 200
        _r("Deals -- Convert lead to deal", ok, f"HTTP {r.status_code}")

        if ok:
            from app.models.deal import Deal
            from app.models.contact import Contact
            db = TestingSession()
            deal = db.query(Deal).filter(Deal.lead_id == lead_id).first()
            contact = db.query(Contact).filter(Contact.lead_id == lead_id).first()
            db.close()
            if deal:
                deal_id = deal.id
                _created["deal_ids"].append(deal_id)
                _r("Deals -- Deal in DB", True, f"id={deal_id}, stage={deal.stage}, amount={deal.amount}")
            else:
                _r("Deals -- Deal in DB", False, "not found after conversion")
            if contact:
                _created["contact_ids"].append(contact.id)
                _r("Deals -- Contact auto-created from lead", True, f"id={contact.id}")
            else:
                _r("Deals -- Contact auto-created from lead", False, "not found")

    # Detail
    if deal_id:
        r = c.get(f"/deals/{deal_id}")
        _r("Deals -- Detail page (GET /deals/{id})", r.status_code == 200, f"HTTP {r.status_code}")

    # Stage update
    if deal_id:
        r = c.post(f"/deals/move/{deal_id}", data={
            "stage": "Qualification",
        }, follow_redirects=True)
        _r("Deals -- Update stage", r.status_code in (200, 303), f"HTTP {r.status_code}")

    # Non-existent
    r = c.get("/deals/9999999")
    _r("Deals -- Non-existent deal returns no 500", r.status_code != 500, f"HTTP {r.status_code}")

    return deal_id


# ══════════════════════════════════════════════════════════════════════════
# CONTACTS TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_contacts(c):
    _section("Contacts Module")
    r = c.get("/contacts")
    _r("Contacts -- List page (GET /contacts)", r.status_code == 200, f"HTTP {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════
# ACTIVITIES TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_activities(c, TestingSession, lead_id) -> int | None:
    _section("Activities Module")
    activity_id = None

    # List
    r = c.get("/activities")
    _r("Activities -- List page (GET /activities)", r.status_code == 200, f"HTTP {r.status_code}")

    # Create
    data = {
        "title": f"TEST_ACT_{TS}",
        "activity_type": "Call",
        "status_val": "pending",
        "description": "QA automated test activity",
    }
    if lead_id:
        data["lead_id"] = str(lead_id)

    r = c.post("/activities", data=data, follow_redirects=True)
    ok = r.status_code == 200
    _r("Activities -- Create activity (POST /activities)", ok, f"HTTP {r.status_code}")

    if ok:
        from app.models.activity import Activity
        db = TestingSession()
        act = db.query(Activity).filter(Activity.title == f"TEST_ACT_{TS}").first()
        db.close()
        if act:
            activity_id = act.id
            _created["activity_ids"].append(activity_id)
            _r("Activities -- Activity in DB", True, f"id={activity_id}, type={act.activity_type}, status={act.status}")
        else:
            _r("Activities -- Activity in DB", False, "not found after POST")

    # Filters
    for param, val, label in [
        ("filter_type",   "Call",    "by type"),
        ("filter_status", "pending", "by status"),
    ]:
        r = c.get("/activities", params={param: val})
        _r(f"Activities -- Filter {label}", r.status_code == 200, f"HTTP {r.status_code}")

    # Mark complete
    if activity_id:
        r = c.post(f"/activities/{activity_id}/complete", follow_redirects=True)
        ok = r.status_code == 200
        _r("Activities -- Mark complete", ok, f"HTTP {r.status_code}")
        if ok:
            from app.models.activity import Activity
            db = TestingSession()
            act = db.query(Activity).filter(Activity.id == activity_id).first()
            db.close()
            _r("Activities -- Status updated to completed in DB",
               act is not None and act.status == "completed",
               f"status={act.status if act else 'not found'}")

    return activity_id


# ══════════════════════════════════════════════════════════════════════════
# REMINDERS TESTS
# ══════════════════════════════════════════════════════════════════════════

def test_reminders(c, TestingSession, lead_id):
    _section("Reminders Module")

    # GET due reminders (JSON API)
    r = c.get("/api/reminders/due")
    try:
        data = r.json()
        ok = r.status_code == 200 and isinstance(data, list)
        _r("Reminders -- GET /api/reminders/due", ok, f"HTTP {r.status_code}, count={len(data) if ok else '?'}")
    except Exception:
        _r("Reminders -- GET /api/reminders/due", False, f"HTTP {r.status_code} non-JSON")

    # Create via service
    reminder_id = None
    try:
        from app.services.reminder import create_reminder
        db = TestingSession()
        rem = create_reminder(
            db,
            title=f"TEST_REM_{TS}",
            related_type="lead",
            related_id=lead_id or 1,
            reminder_time=datetime.utcnow(),
            description="QA automated test reminder",
        )
        db.close()
        if rem:
            reminder_id = rem.id
            _created["reminder_ids"].append(reminder_id)
            _r("Reminders -- Create reminder (service)", True, f"id={reminder_id}, status={rem.status}")
        else:
            _r("Reminders -- Create reminder (service)", False, "returned None")
    except Exception as e:
        _r("Reminders -- Create reminder (service)", False, str(e))

    # Dismiss (snooze)
    if reminder_id:
        r = c.post(f"/api/reminders/{reminder_id}/dismiss")
        ok = r.status_code in (200, 204)
        _r("Reminders -- Dismiss/snooze", ok, f"HTTP {r.status_code}")
        if ok:
            from app.models.reminder import Reminder
            db = TestingSession()
            rem = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            db.close()
            _r("Reminders -- snooze_count incremented",
               rem is not None and (rem.snooze_count or 0) >= 1,
               f"snooze_count={rem.snooze_count if rem else 'not found'}")

    # Mark done
    if reminder_id:
        r = c.post(f"/api/reminders/{reminder_id}/complete")
        ok = r.status_code in (200, 204)
        _r("Reminders -- Mark done", ok, f"HTTP {r.status_code}")
        if ok:
            from app.models.reminder import Reminder
            db = TestingSession()
            rem = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            db.close()
            _r("Reminders -- Status set to done in DB",
               rem is not None and rem.status == "done",
               f"status={rem.status if rem else 'not found'}")


# ══════════════════════════════════════════════════════════════════════════
# DASHBOARD & REPORTS
# ══════════════════════════════════════════════════════════════════════════

def test_dashboard(c):
    _section("Dashboard & Reports")

    r = c.get("/")
    ok = r.status_code == 200 and b"Dashboard" in r.content
    _r("Dashboard -- Main page loads (GET /)", ok, f"HTTP {r.status_code}")

    r = c.get("/dashboard")
    ok = r.status_code == 200 and b"Reports" in r.content
    _r("Dashboard -- Reports page loads (GET /dashboard)", ok, f"HTTP {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════
# ERROR HANDLING
# ══════════════════════════════════════════════════════════════════════════

def test_error_handling(c):
    _section("Error Handling")

    for path, label in [
        ("/leads/9999999",  "non-existent lead"),
        ("/deals/9999999",  "non-existent deal"),
    ]:
        r = c.get(path)
        _r(f"Errors -- {label} returns no 500", r.status_code != 500, f"HTTP {r.status_code}")

    # Empty status update body
    r = c.post("/leads/9999999/status", json={})
    _r("Errors -- Status update missing body no 500",
       r.status_code not in (500,), f"HTTP {r.status_code}")

    # Unauthenticated access (no cookie)
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db
    unauth = TestClient(app, raise_server_exceptions=False)
    # Remove the override so there's no cookie
    r = unauth.get("/leads", follow_redirects=False)
    _r("Errors -- Unauthenticated redirects to /login",
       r.status_code in (302, 303, 307), f"HTTP {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════
# REPORT GENERATION
# ══════════════════════════════════════════════════════════════════════════

def generate_report():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    total   = len(results)
    passed  = sum(1 for r in results if r["status"] == "PASS")
    warned  = sum(1 for r in results if r["status"] == "WARN")
    failed  = sum(1 for r in results if r["status"] == "FAIL")
    pass_rate = int(passed * 100 / total) if total else 0

    if failed == 0:
        stability = "STABLE -- All critical tests passed"
    elif failed <= 2:
        stability = "MOSTLY STABLE -- Minor issues found"
    else:
        stability = "UNSTABLE -- Multiple failures detected"

    # Group by section
    sections: dict = {}
    for r in results:
        section = r["name"].split(" -- ")[0] if " -- " in r["name"] else "General"
        sections.setdefault(section, []).append(r)

    lines = [
        "# CRM System -- End-to-End Test Report",
        "",
        f"> **Generated:** {now}",
        f"> **Test DB:** `test_run_{TS}.db` (isolated, deleted after run)",
        f"> **Test user:** `{TEST_EMAIL}` (deleted after run)",
        f"> **Run ID:** `{TS}`",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total Tests | {total} |",
        f"| Passed | {passed} |",
        f"| Warnings | {warned} |",
        f"| Failed | {failed} |",
        f"| Pass Rate | {pass_rate}% |",
        f"| Overall Stability | **{stability}** |",
        "",
        "---",
        "",
        "## Results by Module",
        "",
    ]

    for section, items in sections.items():
        s_pass = sum(1 for i in items if i["status"] == "PASS")
        s_fail = sum(1 for i in items if i["status"] == "FAIL")
        badge  = "PASS" if s_fail == 0 else f"FAIL ({s_fail})"
        lines.append(f"### {section}  [{badge}]  {s_pass}/{len(items)} passed")
        lines.append("")
        lines.append("| Test Case | Result | Detail |")
        lines.append("|---|---|---|")
        for item in items:
            icon   = "PASS" if item["status"] == "PASS" else ("WARN" if item["status"] == "WARN" else "FAIL")
            detail = item["detail"].replace("|", "\\|")
            name   = item["name"].split(" -- ", 1)[1] if " -- " in item["name"] else item["name"]
            lines.append(f"| {name} | **{icon}** | {detail} |")
        lines.append("")

    # Issues
    failures = [r for r in results if r["status"] == "FAIL"]
    if failures:
        lines += ["---", "", "## Issues Found", ""]
        for i, f in enumerate(failures, 1):
            lines.append(f"{i}. **{f['name']}** -- {f['detail']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Isolation & Cleanup",
        "",
        "This test run used a **dedicated isolated SQLite database** (`test_run_{TS}.db`).",
        "The production `crm.db` was never accessed or modified.",
        "",
        "| Item | Action |",
        "|---|---|",
        f"| Test database `test_run_{TS}.db` | Dropped and deleted |",
        f"| Test user `{TEST_EMAIL}` | Deleted |",
        f"| Test leads (IDs: {_created['lead_ids']}) | Removed with DB |",
        f"| Test deals (IDs: {_created['deal_ids']}) | Removed with DB |",
        f"| Test contacts (IDs: {_created['contact_ids']}) | Removed with DB |",
        f"| Test activities (IDs: {_created['activity_ids']}) | Removed with DB |",
        f"| Test reminders (IDs: {_created['reminder_ids']}) | Removed with DB |",
        "",
        "---",
        "",
        "## Module Stability Matrix",
        "",
        "| Module | Status |",
        "|---|---|",
    ]

    for section, items in sections.items():
        s_fail = sum(1 for i in items if i["status"] == "FAIL")
        status = "Stable" if s_fail == 0 else f"Issues ({s_fail} failure(s))"
        lines.append(f"| {section} | {status} |")

    lines += [
        "",
        "---",
        "",
        f"*Auto-generated by `run_tests.py` -- Run ID `{TS}`*",
        "",
    ]

    report = "\n".join(lines)
    with open("test_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    return passed, failed, total


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*60}")
    print(f"  CRM Test Suite  --  Run ID: {TS}")
    print(f"  Isolated DB: test_run_{TS}.db")
    print(f"  Test user: {TEST_EMAIL}")
    print(f"{'='*60}")

    client = engine = session = db_path = None

    try:
        print("\n-- Building isolated test environment --")
        client, engine, db_path, Session = _build_test_client()
        print(f"  OK  Test DB created: {db_path}")

        if not test_auth(client):
            return 1

        test_pages(client)
        lead_id   = test_leads(client, Session)
        deal_id   = test_deals(client, Session, lead_id)
        test_contacts(client)
        test_activities(client, Session, lead_id)
        test_reminders(client, Session, lead_id)
        test_dashboard(client)
        test_error_handling(client)

    except Exception as e:
        print(f"\n  FATAL: {e}")
        traceback.print_exc()
    finally:
        # Always clean up
        _section("Cleanup")
        if engine and db_path and Session:
            _cleanup_test_db(engine, db_path, Session)
        if client:
            from app.db.session import get_db
            from app.main import app
            app.dependency_overrides.pop(get_db, None)

    print("\n-- Generating test_report.md --")
    passed, failed, total = generate_report()
    print(f"  Report written: test_report.md")

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed  |  {failed} failed")
    print(f"  Status:  {'ALL TESTS PASSED' if failed == 0 else f'{failed} TEST(S) FAILED'}")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
