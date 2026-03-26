from app.models.lead import Lead

def calculate_lead_score(lead: Lead) -> int:
    """
    Simple rule-based lead scoring logic.
    Returns a score out of 100.
    """
    score = 0
    # Business email vs personal
    if lead.email:
        if not lead.email.endswith(("@gmail.com", "@yahoo.com", "@hotmail.com")):
            score += 40
        else:
            score += 15
            
    # Company provided
    if lead.company:
        score += 30
        
    # Phone provided
    if lead.phone:
        score += 20
        
    # Full name provided
    if lead.first_name and lead.last_name:
        score += 10
        
    return min(score, 100)

def generate_followup_email(lead: Lead) -> str:
    """
    Mock AI generator that creates personalized follow-up emails based on lead data.
    """
    company_context = f" at {lead.company}" if lead.company else ""
    first_name = lead.first_name or "there"
    
    draft = f"""Subject: Optimizing your sales process{company_context}

Hi {first_name},

I noticed your interest regarding our solutions. Considering you are exploring CRM options{company_context}, I wanted to reach out.

Our platform is designed to streamline your workflows, automate task tracking, and provide clear pipeline visibility without the usual complexity of enterprise tools.

I'd love to schedule a quick 10-minute call this week to show you how we can specifically help your team. 

Do you have any availability on Tuesday or Thursday?

Best regards,
Your AI Sales Assistant
"""
    return draft
