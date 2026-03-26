from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.schemas.activity import ActivityCreate
from app.services import activity as activity_service

def on_lead_created(db: Session, lead: Lead):
    """
    Workflow Automation Trigger: New Lead Created
    Action: Auto-generate a follow-up task
    """
    activity_service.create_activity(db, ActivityCreate(
        title="Follow up with new lead",
        activity_type="Task",
        description=f"Auto-assigned: Follow up with new lead {lead.first_name} {lead.last_name}",
        lead_id=lead.id
    ))

def on_lead_status_changed(db: Session, lead: Lead, old_status: str, new_status: str):
    """
    Workflow Automation Trigger: Lead Status Changed
    Action: Conditional task creation based on new status
    """
    if new_status == "Qualified":
        activity_service.create_activity(db, ActivityCreate(
            title="Prepare and review proposal",
            activity_type="Task",
            description=f"Automated: Prepare and review proposal for {lead.first_name} {lead.last_name}",
            lead_id=lead.id
        ))

    elif new_status == "Contacted":
        activity_service.create_activity(db, ActivityCreate(
            title="Follow-up check-in",
            activity_type="Task",
            description=f"Automated: Check back with {lead.first_name} in 48 hours",
            lead_id=lead.id
        ))

    elif new_status == "Proposal Sent":
        activity_service.create_activity(db, ActivityCreate(
            title="Await proposal response",
            activity_type="Task",
            description=f"Automated: Follow up on proposal sent to {lead.first_name} {lead.last_name}",
            lead_id=lead.id
        ))
