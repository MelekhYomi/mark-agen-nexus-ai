from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved from this file's own location, not the process's working directory,
# so the app behaves the same regardless of where it's launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_PATH), extra="ignore")

    APP_NAME: str = "Nexus AI"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # SECURITY - Keep your existing keys but simplify for demo
    SECRET_KEY: str = "dev-secret-key-for-hackathon-123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # DATABASE - FORCE SQLITE FOR IMMEDIATE DEMO
    DATABASE_URL: str = "sqlite:///./nexus_demo.db"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"

    LOG_LEVEL: str = "info"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Dev-only default. A real deployment must set this via env var.
    TOKEN_ENCRYPTION_KEY: str = "8MlE6JuIb-yhbnH0uuoLzcv7Kj0DLjm5n6MKZ3zChMk="
    OAUTH_STATE_SECRET: str = "dev-oauth-state-secret"

    # ALIBABA CLOUD / QWEN CONFIG
    DASHSCOPE_API_KEY: str = "sk-placeholder-key"
    # Native dashscope SDK path (NOT /compatible-mode/v1 - that's for OpenAI-SDK-style calls only)
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    QWEN_MODEL_MAX: str = "qwen-max"
    QWEN_MODEL_TURBO: str = "qwen-turbo"

    # Payments (unused by the agent demo; placeholders so imports don't crash)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    COINBASE_API_KEY: str = ""
    COINBASE_WEBHOOK_SECRET: str = ""

    # Email (unused by the agent demo; placeholders so imports don't crash)
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@nexusai.com"
    SENDGRID_FROM_NAME: str = "Nexus AI"

    # Social OAuth (unused by the agent demo; placeholders so imports don't crash)
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_REDIRECT_URI: str = ""
    TIKTOK_APP_ID: str = ""
    TIKTOK_APP_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = ""
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    TWITTER_REDIRECT_URI: str = ""
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    PINTEREST_CLIENT_ID: str = ""
    PINTEREST_CLIENT_SECRET: str = ""
    PINTEREST_REDIRECT_URI: str = ""

settings = Settings()
