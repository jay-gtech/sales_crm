from sqlalchemy.orm import Session
from app.models.activity import Activity
from app.schemas.activity import ActivityCreate


def get_activities(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(Activity)
        .order_by(Activity.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_activities_by_lead(db: Session, lead_id: int):
    return (
        db.query(Activity)
        .filter(Activity.lead_id == lead_id)
        .order_by(Activity.created_at.desc())
        .all()
    )


def get_activities_by_deal(db: Session, deal_id: int):
    return (
        db.query(Activity)
        .filter(Activity.deal_id == deal_id)
        .order_by(Activity.created_at.desc())
        .all()
    )


def create_activity(db: Session, activity: ActivityCreate) -> Activity:
    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity


def mark_complete(db: Session, activity_id: int) -> Activity | None:
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if activity:
        activity.status = "completed"
        db.add(activity)
        db.commit()
        db.refresh(activity)
    return activity


def log_activity(
    db: Session,
    title: str,
    activity_type: str = "Task",
    description: str = "",
    lead_id: int | None = None,
    deal_id: int | None = None,
    status: str = "completed",
) -> None:
    """
    Auto-log helper — used by lead/deal services to record system events.
    Wrapped in try/except so it never crashes the calling service.
    """
    try:
        activity = Activity(
            title=title,
            activity_type=activity_type,
            status=status,
            description=description,
            lead_id=lead_id,
            deal_id=deal_id,
        )
        db.add(activity)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[activity] log_activity failed (non-critical): {exc}")
