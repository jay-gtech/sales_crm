import re
from sqlalchemy.orm import Session
from app.models.meeting import Meeting, MeetingInsight
from app.schemas.meeting import MeetingCreate
from app.schemas.activity import ActivityCreate
from app.services import activity as activity_service

def process_transcript(text: str):
    """
    Rule-based extraction to identify Tasks and Discussion Points.
    """
    sentences = [s.strip() for s in text.replace('\n', '.').split('.') if s.strip()]
    tasks = []
    points = []
    
    task_keywords = ["will", "should", "need to", "must", "action item"]
    
    for s in sentences:
        is_task = any(kw in s.lower() for kw in task_keywords)
        if is_task:
            deadline = None
            owner = None
            
            # Basic deadline parsing
            match = re.search(r'(by [a-zA-Z0-9 ]+|tomorrow|next week|end of week)', s.lower())
            if match:
                deadline = match.group(0).title()
            
            # Basic owner parsing (word before "will" or "needs to")
            words = s.split()
            lower_words = [w.lower() for w in words]
            for kw in ["will", "must", "should"]:
                if kw in lower_words:
                    idx = lower_words.index(kw)
                    if idx > 0 and len(words[idx-1]) > 2:
                        # check if it's "we" or "i", if so default to unassigned or map to user. We'll leave as is.
                        owner = words[idx-1].capitalize()
                    break
                    
            tasks.append({"content": s, "deadline": deadline, "owner": owner})
        else:
            if len(s) > 15: # Ignore very short conversational filler
                points.append({"content": s})
                
    return tasks, points

def process_meeting(db: Session, meeting_in: MeetingCreate, user_id: int):
    # Enforce performance rule: max 5000 chars
    transcript = meeting_in.transcript[:5000]
    
    # 1. Save Meeting
    db_meeting = Meeting(title=meeting_in.title, transcript=transcript, created_by=user_id)
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    
    # 2. Extract Insights
    tasks, points = process_transcript(transcript)
    
    # 3. Store Insights and Create Activities
    for p in points:
        insight = MeetingInsight(meeting_id=db_meeting.id, type="point", content=p["content"])
        db.add(insight)
        
    for t in tasks:
        insight = MeetingInsight(meeting_id=db_meeting.id, type="task", content=t["content"], deadline=t["deadline"], owner=t["owner"])
        db.add(insight)
        
        # Link to Activity Module
        owner_text = f"Assigned to {t['owner']}: " if t['owner'] and t['owner'].lower() not in ["i", "we", "they"] else ""
        deadline_text = f" [Due: {t['deadline']}]" if t['deadline'] else ""
        
        activity_desc = f"{owner_text}{t['content']}{deadline_text} (From Meeting: {db_meeting.title})"
        
        activity_service.create_activity(db, ActivityCreate(
            activity_type="Task",
            description=activity_desc
        ))
        
    db.commit()
    db.refresh(db_meeting)
    return db_meeting
