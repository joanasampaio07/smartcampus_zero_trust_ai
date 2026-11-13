from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "SmartCampus Zero Trust AI"
    environment: str = "development"
    secret_key: str = "unsafe-dev-secret-change-me"
    access_token_expire_minutes: int = 20
    database_url: str = "sqlite:///./smartcampus.db"
    cors_origins: str = "http://localhost:5173"
    admin_email: str | None = None
    admin_password: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    redis_url: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def allowed_origins(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings():
    return Settings()
settings = get_settings()
