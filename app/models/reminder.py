from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from app.db.base_class import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    related_type = Column(String, nullable=True)   # "lead", "deal", "activity"
    related_id = Column(Integer, nullable=True)
    reminder_time = Column(DateTime, nullable=False)
    status = Column(String, default="pending")      # "pending" | "done"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Snooze tracking
    last_shown_at = Column(DateTime, nullable=True)   # when the popup last appeared
    snooze_count = Column(Integer, default=0)         # how many times user dismissed
