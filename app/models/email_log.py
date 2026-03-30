"""
EmailLog — persists every outbound email attempt (sent or failed).

Fields:
  to_email      — recipient address
  subject       — email subject line
  body          — plain-text body that was sent
  status        — "sent" | "failed"
  related_type  — "lead" | "deal" | None (for generic sends)
  related_id    — PK of the related lead/deal row
  sent_by_id    — user.id who triggered the send
  created_at    — UTC timestamp
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base_class import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id           = Column(Integer, primary_key=True, index=True)
    to_email     = Column(String(320), nullable=False, index=True)
    subject      = Column(String(998), nullable=False)
    body         = Column(Text, nullable=True)
    status       = Column(String(10), nullable=False, default="sent")   # "sent" | "failed"
    related_type = Column(String(20), nullable=True)                    # "lead" | "deal"
    related_id   = Column(Integer, nullable=True, index=True)
    sent_by_id   = Column(Integer, nullable=True)                       # user.id
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
