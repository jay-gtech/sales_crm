from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey
from datetime import datetime
from app.db.base_class import Base
from sqlalchemy.orm import relationship

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    trigger_event = Column(String, nullable=False) # e.g., "lead_status_changed"
    created_at = Column(DateTime, default=datetime.utcnow)

    rules = relationship("WorkflowRule", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowRule(Base):
    __tablename__ = "workflow_rules"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    condition_field = Column(String, nullable=False) # e.g., "status"
    condition_value = Column(String, nullable=False) # e.g., "Qualified"
    action_type = Column(String, nullable=False)    # e.g., "create_task", "assign_owner"
    action_config = Column(JSON, nullable=True)     # e.g., {"task_name": "Review Proposal"}

    workflow = relationship("Workflow", back_populates="rules")
