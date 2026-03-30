from typing import List, Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.lead_history import LeadHistory
from app.schemas.lead import LeadCreate

def get_leads(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, status: Optional[str] = None, owner_id: Optional[int] = None, sort_by: Optional[str] = None, source: Optional[str] = None):
    query = db.query(Lead)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Lead.first_name.ilike(search_filter)) |
            (Lead.last_name.ilike(search_filter)) |
            (Lead.company.ilike(search_filter)) |
            (Lead.email.ilike(search_filter))
        )
    if status and status != 'All':
        query = query.filter(Lead.status == status)
    if source and source != 'All':
        query = query.filter(Lead.source == source)
    if owner_id:
        query = query.filter(Lead.owner_id == owner_id)
    
    # Sorting logic
    if sort_by:
        if sort_by == 'lead_score':
            query = query.order_by(Lead.lead_score.desc())
        elif hasattr(Lead, sort_by):
            query = query.order_by(getattr(Lead, sort_by).asc())
    else:
        query = query.order_by(Lead.id.desc())
        
    return query.offset(skip).limit(limit).all()

def get_lead(db: Session, lead_id: int):
    return db.query(Lead).filter(Lead.id == lead_id).first()

def create_lead(db: Session, lead: LeadCreate):
    # Pre-check: reject duplicate email before hitting the DB constraint
    if lead.email:
        existing = db.query(Lead).filter(Lead.email == lead.email).first()
        if existing:
            import logging
            logging.getLogger(__name__).warning(
                "[lead] create blocked — email already exists: %s", lead.email
            )
            return None   # caller must check for None

    db_lead = Lead(**lead.dict())
    db.add(db_lead)
    try:
        db.commit()
    except Exception as exc:
        # Belt-and-suspenders: catches IntegrityError from a race condition
        db.rollback()
        import logging
        logging.getLogger(__name__).error("[lead] create_lead commit failed: %s", exc)
        return None
    db.refresh(db_lead)
    # Auto-activity: record that a new lead was created
    from app.services.activity import log_activity
    log_activity(
        db, title="New lead created",
        activity_type="Task",
        description=f"Lead {db_lead.first_name} {db_lead.last_name} was added to the CRM.",
        lead_id=db_lead.id,
    )
    # Auto-reminder: follow up in 2 days (safe — never breaks lead creation)
    try:
        from app.services.reminder import create_reminder
        from datetime import datetime
        create_reminder(
            db,
            title=f"Follow up with {db_lead.first_name} {db_lead.last_name} (Lead)",
            related_type="lead",
            related_id=db_lead.id,
            reminder_time=datetime.utcnow(),  # immediately due for demo
            description=f"New lead from {db_lead.company or 'unknown company'}. Follow up!",
        )
    except Exception as e:
        print(f"[REMINDER] Could not create lead reminder: {e}")
    return db_lead

def update_lead_status(db: Session, lead_id: int, new_status: str, user_id: int, notes: Optional[str] = None):
    lead = get_lead(db, lead_id)
    if not lead:
        return None
    
    old_status = lead.status
    if old_status == new_status:
        return lead
    
    # 1. Update Lead
    lead.status = new_status
    db.add(lead)
    
    # 2. Record History
    history = LeadHistory(
        lead_id=lead_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_id=user_id,
        notes=notes
    )
    db.add(history)
    db.commit()
    db.refresh(lead)
    # Auto-activity: record the status change
    from app.services.activity import log_activity
    log_activity(
        db, title=f"Lead status changed to {new_status}",
        activity_type="Task",
        description=f"Status updated from '{old_status}' → '{new_status}'." + (f" Notes: {notes}" if notes else ""),
        lead_id=lead_id,
    )
    # Auto-reminder: next action after status change (safe)
    try:
        from app.services.reminder import create_reminder
        from datetime import datetime
        create_reminder(
            db,
            title=f"Next action for Lead #{lead_id} → {new_status}",
            related_type="lead",
            related_id=lead_id,
            reminder_time=datetime.utcnow(),  # immediately due for demo
            description=f"Lead status changed to '{new_status}'. Plan your next step.",
        )
    except Exception as e:
        print(f"[REMINDER] Could not create status-change reminder: {e}")
    return lead

def update_lead_score(db: Session, lead_id: int):
    lead = get_lead(db, lead_id)
    if not lead:
        return None
    
    score = 0
    # Simple rule-based scoring
    if lead.status == 'Qualified': score += 50
    elif lead.status == 'Contacted': score += 20
    elif lead.status == 'Proposal Sent': score += 70
    elif lead.status == 'Negotiation': score += 80
    
    if lead.email and lead.company: score += 10
    if lead.phone: score += 5
    if lead.source == 'LinkedIn': score += 15
    
    lead.lead_score = score
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

def get_lead_by_email(db: Session, email: str):
    return db.query(Lead).filter(Lead.email == email).first()

def get_lead_by_phone(db: Session, phone: str):
    return db.query(Lead).filter(Lead.phone == phone).first()

def delete_lead(db: Session, lead_id: int) -> bool:
    lead = get_lead(db, lead_id)
    if not lead:
        return False
    db.delete(lead)
    db.commit()
    return True

def convert_lead_to_deal(db: Session, lead_id: int, user_id: int, deal_name: str, deal_amount: float):
    lead = get_lead(db, lead_id)
    if not lead:
        return None
    
    # 1. Create Contact from Lead (reuse existing if email already taken)
    from app.models.contact import Contact
    existing_contact = db.query(Contact).filter(Contact.email == lead.email).first()
    if existing_contact:
        contact = existing_contact
        # Update lead_id link if not set
        if not contact.lead_id:
            contact.lead_id = lead.id
            db.add(contact)
            db.commit()
    else:
        contact = Contact(
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            phone=lead.phone,
            account_name=lead.company,
            lead_id=lead.id
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
    
    # 2. Create Deal
    from app.models.deal import Deal
    from app.models.deal_history import DealHistory
    db_deal = Deal(
        name=deal_name,
        amount=deal_amount,
        contact_id=contact.id,
        lead_id=lead.id,
        owner_id=user_id,
        stage="New"
    )
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    
    # 3. Create initial history
    history = DealHistory(
        deal_id=db_deal.id,
        new_stage="New",
        changed_by_id=user_id
    )
    db.add(history)
    
    # 4. Update lead status
    lead.status = "Converted"
    db.add(lead)
    
    db.commit()
    db.refresh(db_deal)
    return db_deal
