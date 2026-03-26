from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base


class Deal(Base):
    __tablename__ = "deals"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Core fields
    name = Column(String, index=True, nullable=False)
    amount = Column(Float, default=0.0)
    description = Column(String, nullable=True)
    stage = Column(String, default="New")   # New | Qualification | Needs Analysis | Proposal | Negotiation | Closed Won | Closed Lost
    closing_date = Column(DateTime, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    last_stage_change = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, server_default="1")
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="deals", foreign_keys=[owner_id])
    contact = relationship("Contact", back_populates="deals", foreign_keys=[contact_id])
    lead = relationship("Lead", back_populates="deals", foreign_keys=[lead_id])
    activities = relationship("Activity", back_populates="deal")
    history = relationship("DealHistory", back_populates="deal", cascade="all, delete-orphan")
