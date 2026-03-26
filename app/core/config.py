from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CRM Platform"
    SECRET_KEY: str = "supersecretkey"  # change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./crm.db"
    # Set to False before going to production to disable demo console logging and badge
    DEMO_MODE: bool = True

    class Config:
        case_sensitive = True

settings = Settings()
