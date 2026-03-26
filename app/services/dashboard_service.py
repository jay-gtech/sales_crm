from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.lead import Lead
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.meeting import Meeting


# ── Phase 6: Reporting data ────────────────────────────────────────────────

def get_report_data(db: Session) -> dict:
    """
    Extended metrics for the /dashboard reporting page.
    Completely isolated from get_dashboard_data — safe to call independently.
    Wraps everything in try/except so a DB hiccup never crashes the page.
    """
    try:
        total_leads = db.query(func.count(Lead.id)).scalar() or 0

        converted_leads = db.query(func.count(Lead.id)).filter(
            Lead.status.in_(["Won/Lost", "Converted"])
        ).scalar() or 0

        _raw_rate = converted_leads * 100.0 / total_leads if total_leads > 0 else 0.0
        conversion_rate: float = int(_raw_rate * 10) / 10.0  # 1 decimal place

        # Leads by status
        status_rows = (
            db.query(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
            .order_by(func.count(Lead.id).desc())
            .all()
        )
        leads_by_status = [
            {"status": s or "Unknown", "count": c} for s, c in status_rows
        ]

        # Leads by source
        source_rows = (
            db.query(Lead.source, func.count(Lead.id))
            .group_by(Lead.source)
            .order_by(func.count(Lead.id).desc())
            .all()
        )
        leads_by_source = [
            {"source": s or "Direct / Unknown", "count": c} for s, c in source_rows
        ]

        # Deal pipeline totals
        total_deal_value = db.query(func.sum(Deal.amount)).scalar() or 0.0
        won_deal_value = (
            db.query(func.sum(Deal.amount))
            .filter(Deal.stage == "Closed Won")
            .scalar() or 0.0
        )
        total_deals = db.query(func.count(Deal.id)).scalar() or 0
        won_deals = (
            db.query(func.count(Deal.id))
            .filter(Deal.stage == "Closed Won")
            .scalar() or 0
        )

        # Deals by stage
        stage_rows = (
            db.query(Deal.stage, func.count(Deal.id), func.sum(Deal.amount))
            .group_by(Deal.stage)
            .all()
        )
        deals_by_stage = [
            {"stage": s or "Unknown", "count": c, "value": float(v or 0)}
            for s, c, v in stage_rows
        ]

        # 5 most recent leads
        recent_leads = (
            db.query(Lead).order_by(Lead.created_at.desc()).limit(5).all()
        )

        # Lightweight insights — plain strings for demo display
        insights = []
        if leads_by_source:
            top_src = leads_by_source[0]
            src_label = top_src["source"].replace("_", " ").title()
            insights.append(f"Most leads come from {src_label} ({top_src['count']} leads)")
        if conversion_rate > 0:
            insights.append(f"Overall lead-to-deal conversion rate is {conversion_rate}%")
        if leads_by_status:
            top_stage = leads_by_status[0]
            insights.append(f"Largest lead pool is in '{top_stage['status']}' stage ({top_stage['count']} leads)")
        if won_deals > 0 and total_deals > 0:
            win_rate = int(won_deals * 100 / total_deals)
            insights.append(f"Deal win rate is {win_rate}% ({won_deals} of {total_deals} deals closed won)")
        if not insights:
            insights.append("Add leads and deals to start seeing actionable insights here.")

        return {
            "total_leads": total_leads,
            "converted_leads": converted_leads,
            "conversion_rate": conversion_rate,
            "leads_by_status": leads_by_status,
            "leads_by_source": leads_by_source,
            "total_deal_value": total_deal_value,
            "won_deal_value": won_deal_value,
            "total_deals": total_deals,
            "won_deals": won_deals,
            "deals_by_stage": deals_by_stage,
            "recent_leads": recent_leads,
            "insights": insights,
        }

    except Exception as exc:
        print(f"[dashboard] get_report_data failed: {exc}")
        # Safe fallback — never crash the page
        return {
            "total_leads": 0,
            "converted_leads": 0,
            "conversion_rate": 0.0,
            "leads_by_status": [],
            "leads_by_source": [],
            "total_deal_value": 0.0,
            "won_deal_value": 0.0,
            "total_deals": 0,
            "won_deals": 0,
            "deals_by_stage": [],
            "recent_leads": [],
            "insights": ["Add leads and deals to start seeing actionable insights here."],
        }

def get_dashboard_data(db: Session, user_id: int):
    # Retrieve aggregated counts
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    
    active_deals = db.query(func.count(Deal.id)).filter(
        Deal.stage.notin_(["Closed Won", "Closed Lost"])
    ).scalar() or 0
    
    won_deals = db.query(func.count(Deal.id)).filter(
        Deal.stage == "Closed Won"
    ).scalar() or 0
    
    tasks_count = db.query(func.count(Activity.id)).filter(
        Activity.activity_type == "Task"
    ).scalar() or 0
    
    meetings_count = db.query(func.count(Meeting.id)).filter(Meeting.created_by == user_id).scalar() or 0
    
    # Retrieve top 5 recent activities and meetings
    recent_activities = db.query(Activity).order_by(Activity.created_at.desc()).limit(5).all()
    recent_meetings = db.query(Meeting).filter(Meeting.created_by == user_id).order_by(Meeting.created_at.desc()).limit(5).all()
    
    return {
        "total_leads": total_leads,
        "active_deals": active_deals,
        "won_deals": won_deals,
        "tasks_count": tasks_count,
        "meetings_count": meetings_count,
        "recent_activities": recent_activities,
        "recent_meetings": recent_meetings
    }
