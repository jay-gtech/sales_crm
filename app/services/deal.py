from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from app.models.deal import Deal
from app.models.deal_history import DealHistory
from app.schemas.deal import DealCreate, DealUpdate

def get_deals(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    stage: Optional[str] = None,
    owner_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc"
):
    query = db.query(Deal)
    if stage:
        query = query.filter(Deal.stage == stage)
    if owner_id:
        query = query.filter(Deal.owner_id == owner_id)
    if search:
        query = query.filter(Deal.name.ilike(f"%{search}%"))
    
    # Total count for pagination
    total_count = query.count()
    
    # Sorting
    sort_attr = getattr(Deal, sort_by, Deal.created_at)
    if order == "desc":
        query = query.order_by(sort_attr.desc())
    else:
        query = query.order_by(sort_attr.asc())
    
    deals = query.offset(skip).limit(limit).all()
    return deals, total_count

def get_deal(db: Session, deal_id: int):
    return db.query(Deal).filter(Deal.id == deal_id).first()

def create_deal(db: Session, deal: DealCreate, current_user_id: int):
    db_deal = Deal(**deal.model_dump())
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    
    # Record initial stage in history
    history = DealHistory(
        deal_id=db_deal.id,
        new_stage=db_deal.stage,
        changed_by_id=current_user_id
    )
    db.add(history)
    db.commit()

    # Auto-activity: record deal creation
    from app.services.activity import log_activity
    log_activity(
        db, title="Deal created",
        activity_type="Task",
        description=f"Deal '{db_deal.name}' was created at stage '{db_deal.stage}'.",
        deal_id=db_deal.id,
    )
    # Auto-reminder: check deal progress in 2 days (safe)
    try:
        from app.services.reminder import create_reminder
        create_reminder(
            db,
            title=f"Check deal progress: {db_deal.name}",
            related_type="deal",
            related_id=db_deal.id,
            reminder_time=datetime.utcnow(),  # immediately due for demo
            description=f"New deal created at stage '{db_deal.stage}'. Review and push forward!",
        )
    except Exception as e:
        print(f"[REMINDER] Could not create deal reminder: {e}")
    return db_deal

def update_deal(db: Session, deal_id: int, deal: DealUpdate, current_user_id: int):
    db_deal = get_deal(db, deal_id)
    if not db_deal:
        return None
    
    data = deal.model_dump(exclude_unset=True)
    old_stage = db_deal.stage
    new_stage = data.get("stage")
    
    for key, value in data.items():
        setattr(db_deal, key, value)
    
    if new_stage and new_stage != old_stage:
        db_deal.last_stage_change = datetime.utcnow()
        history = DealHistory(
            deal_id=db_deal.id,
            old_stage=old_stage,
            new_stage=new_stage,
            changed_by_id=current_user_id
        )
        db.add(history)

    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)

    if new_stage and new_stage != old_stage:
        from app.services.activity import log_activity
        log_activity(
            db, title=f"Deal moved to {new_stage}",
            activity_type="Task",
            description=f"Stage changed from '{old_stage}' → '{new_stage}'.",
            deal_id=db_deal.id,
        )
    return db_deal

def delete_deal(db: Session, deal_id: int):
    db_deal = get_deal(db, deal_id)
    if db_deal:
        db.delete(db_deal)
        db.commit()
        return True
    return False

def get_pipeline_stats(db: Session):
    # Total pipeline value
    total_value = db.query(func.sum(Deal.amount)).filter(
        Deal.stage.notin_(["Closed Won", "Closed Lost"])
    ).scalar() or 0.0
    
    # Total won value
    won_value = db.query(func.sum(Deal.amount)).filter(
        Deal.stage == "Closed Won"
    ).scalar() or 0.0
    
    # Stage counts and values
    stage_stats = db.query(
        Deal.stage, 
        func.count(Deal.id), 
        func.sum(Deal.amount)
    ).group_by(Deal.stage).all()
    
    return {
        "total_pipeline_value": total_value,
        "total_won_value": won_value,
        "stage_stats": [{"stage": s, "count": c, "value": v or 0.0} for s, c, v in stage_stats]
    }
