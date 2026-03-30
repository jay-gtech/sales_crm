from app.core.email_config import email_settings
from app.core.config import settings

print(f"--- email_settings ---")
print(f"SMTP_SERVER: {email_settings.SMTP_SERVER}")
print(f"SMTP_EMAIL: {email_settings.SMTP_EMAIL}")
print(f"SMTP_PASSWORD (len): {len(email_settings.SMTP_PASSWORD)}")
print(f"SMTP_PASSWORD (first 2): {email_settings.SMTP_PASSWORD[:2]}")

print(f"\n--- core settings ---")
print(f"SMTP_SERVER: {settings.SMTP_SERVER}")
print(f"SMTP_EMAIL: {settings.SMTP_EMAIL}")
print(f"SMTP_PASSWORD (len): {len(settings.SMTP_PASSWORD)}")
