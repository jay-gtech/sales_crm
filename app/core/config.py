from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CRM Platform"
    SECRET_KEY: str = "supersecretkey"  # change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./crm.db"
    # Set to False before going to production to disable demo console logging and badge
    DEMO_MODE: bool = True

    # ── Email (SMTP) — leave empty to disable ─────────────────────────────
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "CRM Platform"

    # ── WhatsApp (Twilio) — leave empty to disable ─────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""    # e.g. "whatsapp:+14155238886"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"               # silently ignore unknown env vars

settings = Settings()
