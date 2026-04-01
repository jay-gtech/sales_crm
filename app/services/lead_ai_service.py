import os
import logging
from typing import Optional
from sqlalchemy.orm import Session
from groq import Groq

from app.models.lead import Lead
from app.models.activity import Activity
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_lead_summary_ai(db: Session, lead_id: int) -> dict:
    """
    Fetches lead data and activities, then generates a summary using Groq.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        return {"lead_id": lead_id, "summary": "Lead not found."}

    # Fetch activities as notes
    activities = db.query(Activity).filter(Activity.lead_id == lead_id).all()
    notes_list = [a.description for a in activities if a.description]
    notes_text = "\n".join(notes_list) if notes_list else "No notes available."

    name = f"{lead.first_name} {lead.last_name}"
    company = lead.company or "Unknown"

    # 1. Try Groq
    try:
        api_key = settings.GROQ_API_KEY
        if api_key:
            client = Groq(api_key=api_key)
            prompt = f"""Summarize the following lead in 2-3 lines for a sales team:
Name: {name}
Company: {company}
Notes: {notes_text}"""

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=settings.LLM_MODEL,
                max_tokens=150,
                temperature=0.5,
            )
            summary = chat_completion.choices[0].message.content.strip()
            return {"lead_id": lead_id, "summary": summary}
    except Exception as e:
        logger.warning(f"[lead_ai] Groq failed: {e}")

    # 2. Fallback: Manual summary
    status = lead.status or "New"
    activity_count = len(activities)
    manual_summary = f"{name} from {company}. Current status: {status}. Interactions: {activity_count} total."
    if not notes_list:
        manual_summary += " No interaction notes found."
    else:
        manual_summary += f" Recent note: {notes_list[0][:50]}..."

    return {"lead_id": lead_id, "summary": manual_summary}
