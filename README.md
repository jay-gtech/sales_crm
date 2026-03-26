# Sales CRM System

A production-ready, full-stack Customer Relationship Management (CRM) system built with FastAPI, SQLAlchemy, and Jinja2. Designed for small-to-medium sales teams to manage leads, deals, activities, and analytics — all in one place.

---

## Features

### Lead Management
- Create, view, update, and delete leads
- Lead status funnel: New → Contacted → Qualified → Proposal Sent → Negotiation → Won/Lost
- Advanced filters: search by name/email/company, filter by status and lead source
- Kanban board and table views
- AI lead scoring with visual score bar
- Lead history tracking with full audit trail
- CSV bulk import and public API lead capture

### Deal Pipeline
- Convert qualified leads into deals in one click
- Visual pipeline stages: New → Qualification → Proposal → Negotiation → Closed Won/Lost
- Stage history timeline with timestamps
- Deal detail view with linked contact and source lead
- Activity log per deal

### Activity Tracking
- Log calls, emails, meetings, and tasks
- Link activities to leads or deals
- Pending / Completed status with one-click completion
- Auto-logged activities on key CRM events (lead created, status changed, deal created)
- Timeline feed with type icons and status badges

### Dashboard & Reports
- KPI summary cards: Total Leads, Active Deals, Won Deals, Tasks, Meetings
- Leads by Status bar chart (funnel drop-off analysis)
- Leads by Source bar chart (channel ROI)
- Deal pipeline value by stage
- AI-generated insights: top source, conversion rate, win rate
- System status indicator (Go-Live readiness)

### Integrations
- Lead Capture REST API (`POST /api/public/lead`) — no auth required
- Mock source endpoints: Facebook, Google Ads, Email, WhatsApp
- AI Meeting Intelligence: paste a transcript → auto-extract tasks and key points
- CRM Assistant chatbot

### Training & Documentation
- In-app Help Guide (`/help`) with step-by-step walkthroughs
- Standard Operating Procedures (`/sop`) — Lead Management, Deal Pipeline, Activity Tracking, Best Practices
- Demo Mode: console-logs every request for visibility during demos

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.10+) |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) — swap to PostgreSQL for production |
| Migrations | Alembic |
| Templates | Jinja2 |
| Styling | Tailwind CSS (CDN) + Font Awesome |
| Auth | JWT (python-jose) + bcrypt password hashing |
| Config | pydantic-settings |

---

## Project Structure

```
sales_crm/
├── app/
│   ├── api/
│   │   ├── deps.py              # Auth dependency (get_current_user)
│   │   ├── endpoints/           # meeting, chatbot
│   │   └── routes/              # leads, deals, activities, contacts, auth, ai, public
│   ├── core/
│   │   └── config.py            # Settings (DEMO_MODE, SECRET_KEY, DB URL)
│   ├── db/
│   │   ├── base.py              # Imports all models for Alembic
│   │   └── session.py           # SQLAlchemy engine + SessionLocal
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/                # Business logic layer
│   ├── static/                  # CSS, JS, images
│   └── templates/               # Jinja2 HTML templates
│       ├── base.html
│       ├── index.html           # Main dashboard
│       ├── leads.html
│       ├── lead_detail.html
│       ├── deals.html
│       ├── deal_detail.html
│       ├── activities.html
│       ├── dashboard.html       # Reports & analytics
│       ├── help.html            # Onboarding guide
│       └── sop.html             # SOP documentation
├── alembic/
│   └── versions/                # Database migration scripts
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- pip or conda

### 1. Clone the repository
```bash
git clone https://github.com/jay-gtech/sales_crm.git
cd sales_crm
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run database migrations
```bash
alembic upgrade head
```

### 5. Start the server
```bash
uvicorn app.main:app --reload
```

The app will be available at: **http://127.0.0.1:8000**

> On first start, 5 sample leads and demo activities are automatically seeded.

---

## Default Login

Register a new account at `/register`, or use the registration form on first visit.

---

## Key Routes

| Route | Description |
|---|---|
| `GET /` | Main dashboard with KPIs |
| `GET /leads` | Leads list (table + kanban) |
| `GET /leads/{id}` | Lead detail with timeline |
| `GET /deals` | Deal pipeline |
| `GET /deals/{id}` | Deal detail |
| `GET /activities` | Activity tracker |
| `GET /dashboard` | Reports & analytics |
| `GET /help` | Onboarding guide |
| `GET /sop` | Standard operating procedures |
| `POST /api/public/lead` | Public lead capture API |
| `POST /api/mock/facebook-lead` | Mock Facebook lead |
| `POST /api/mock/google-lead` | Mock Google Ads lead |

---

## Demo Mode

The app ships with `DEMO_MODE = True` in `app/core/config.py`.

When enabled:
- Every HTTP request is logged to the console with method, path, status, and duration
- An amber "Demo Mode" badge appears in the sidebar
- Startup banner prints system info

To disable for production: set `DEMO_MODE = False` in `app/core/config.py`.

---

## Configuration

Edit `app/core/config.py` to change:

```python
PROJECT_NAME = "CRM Platform"       # App display name
SECRET_KEY = "..."                   # Change before deploying
SQLALCHEMY_DATABASE_URI = "sqlite:///./crm.db"  # Swap for PostgreSQL
DEMO_MODE = True                     # Set False for production
```

---

## Production Notes

- Replace `SECRET_KEY` with a randomly generated 64-character string
- Switch `SQLALCHEMY_DATABASE_URI` to a PostgreSQL connection string
- Run behind a reverse proxy (nginx) with SSL
- Set `DEMO_MODE = False`
- Use environment variables for secrets (`.env` file, excluded from git)

---

## License

MIT — free to use for personal and commercial projects.
