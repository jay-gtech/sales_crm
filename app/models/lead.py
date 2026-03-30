from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, index=True)
    company = Column(String)
    status = Column(String, default="New") # New, Contacted, Qualified, Lost, Converted
    
    # Restored Advanced Fields
    salutation = Column(String, nullable=True)
    secondary_email = Column(String, nullable=True)
    skype_id = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    website = Column(String, nullable=True)
    title = Column(String, nullable=True)
    source = Column(String, nullable=True)          # website, facebook, google_ads, email, whatsapp, manual
    source_details = Column(String, nullable=True)  # free-text detail about capture origin
    lead_score = Column(Integer, default=0)
    rating = Column(Integer, default=0)
    tag = Column(String, nullable=True)
    
    # Conversion & Tracking
    is_converted = Column(Boolean, default=False)
    converted_at = Column(DateTime, nullable=True)
    last_contacted_at = Column(DateTime, nullable=True)
    unsubscribed_mode = Column(String, nullable=True)
    unsubscribed_time = Column(DateTime, nullable=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="leads")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    deals = relationship("Deal", back_populates="lead")
    contacts = relationship("Contact", back_populates="lead")
    activities = relationship("Activity", back_populates="lead")
    lead_history = relationship("LeadHistory", back_populates="lead", cascade="all, delete-orphan")
