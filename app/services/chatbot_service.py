from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.lead import Lead
from app.models.deal import Deal
from app.models.activity import Activity
from app.models.meeting import Meeting

def process_query(query: str, db: Session, user):
    query = query.lower().strip()
    
    # 1. Lead related queries
    if "lead" in query:
        count = db.query(func.count(Lead.id)).scalar() or 0
        recent = db.query(Lead).order_by(Lead.created_at.desc()).limit(3).all()
        lead_list = "\n".join([f"- {l.first_name} {l.last_name} ({l.company})" for l in recent])
        return f"You have {count} total leads. Recent leads are:\n{lead_list}" if count > 0 else "You don't have any leads yet."
        
    # 2. Deal related queries
    if "deal" in query:
        active_count = db.query(func.count(Deal.id)).filter(Deal.stage.notin_(["Won", "Lost"])).scalar() or 0
        won_count = db.query(func.count(Deal.id)).filter(Deal.stage == "Won").scalar() or 0
        return f"Currently, you have {active_count} active deals and {won_count} won deals."
        
    # 3. Task / Activity related queries
    if "task" in query or "activit" in query:
        tasks = db.query(Activity).filter(Activity.activity_type == "Task").order_by(Activity.created_at.desc()).limit(5).all()
        if not tasks:
            return "No recent tasks or activities found."
        task_list = "\n".join([f"- {t.description}" for t in tasks])
        return f"Here are your most recent tasks:\n{task_list}"
        
    # 4. Meeting related queries
    if "meeting" in query:
        count = db.query(func.count(Meeting.id)).filter(Meeting.created_by == user.id).scalar() or 0
        recent = db.query(Meeting).filter(Meeting.created_by == user.id).order_by(Meeting.created_at.desc()).limit(3).all()
        meeting_list = "\n".join([f"- {m.title} ({m.created_at.strftime('%Y-%m-%d')})" for m in recent])
        return f"You've processed {count} meetings with AI. Latest ones:\n{meeting_list}" if count > 0 else "No AI meetings found."

    # Default fallback
    return "I'm not sure how to help with that. Try asking about 'leads', 'deals', 'tasks', or 'meetings'!"
