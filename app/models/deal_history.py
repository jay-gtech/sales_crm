from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class DealHistory(Base):
    __tablename__ = "deal_history"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    old_stage = Column(String)
    new_stage = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    deal = relationship("Deal", back_populates="history")
    changed_by = relationship("User")
