from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    transcript = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    insights = relationship("MeetingInsight", back_populates="meeting", cascade="all, delete-orphan")

class MeetingInsight(Base):
    __tablename__ = "meeting_insights"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    type = Column(String, index=True) # "point", "task"
    content = Column(String, nullable=False)
    deadline = Column(String, nullable=True)
    owner = Column(String, nullable=True)

    meeting = relationship("Meeting", back_populates="insights")
