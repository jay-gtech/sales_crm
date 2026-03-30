from pydantic_settings import BaseSettings

class EmailSettings(BaseSettings):
    """
    Email (SMTP) configuration.
    Values are loaded from environment variables or the .env file.
    """
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "CRM Platform"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

email_settings = EmailSettings()
