from typing import List, Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env explicitly to keep local/dev behavior predictable.
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Required sensitive/runtime settings (no hardcoded defaults).
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    TOTP_ENCRYPTION_KEY: str = ""
    ALLOWED_CORS_ORIGINS_RAW: str = Field(alias="ALLOWED_CORS_ORIGINS")

    # JWT + cookies
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    MFA_TOKEN_EXPIRE_MINUTES: int = 5
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "strict"
    ACCESS_COOKIE_NAME: str = "access_token"
    REFRESH_COOKIE_NAME: str = "refresh_token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Rate limiter
    RATE_LIMIT_MAX_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_KEY_PREFIX: str = "rl"
    RISK_MEDIUM_SCORE_THRESHOLD: int = 40
    RISK_HIGH_SCORE_THRESHOLD: int = 70
    ALERT_EMAIL_TO: str = ""
    ALERT_WEBHOOK_URL: str = ""
    ALERT_WEBHOOK_TIMEOUT_SECONDS: int = 5
    ALERT_WEBHOOK_FORMAT: Literal["auto", "slack", "discord"] = "auto"
    ALERT_MIN_SEVERITY: Literal["low", "medium", "high", "critical"] = "medium"
    OAUTH_STATE_TTL_SECONDS: int = 600
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = ""
    GOOGLE_OAUTH_SCOPES: str = "openid email profile"
    GOOGLE_OAUTH_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_OAUTH_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_OAUTH_USERINFO_URL: str = "https://openidconnect.googleapis.com/v1/userinfo"

    # SMTP (free/self-hosted compatible)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@logonservice.local"
    SMTP_STARTTLS: bool = True
    SECURITY_ALERTS_ENABLED: bool = True
    SECURITY_ALERT_EMAIL: str = ""
    SECURITY_ALERT_EVENT_TYPES_RAW: str = Field(
        default="TOKEN_REUSE_DETECTED,PASSWORD_CHANGED,MFA_ENABLED",
        alias="SECURITY_ALERT_EVENT_TYPES",
    )

    @property
    def ALLOWED_CORS_ORIGINS(self) -> List[str]:
        return self._parse_allowed_origins(self.ALLOWED_CORS_ORIGINS_RAW)

    @classmethod
    def _parse_allowed_origins(cls, value) -> List[str]:
        if isinstance(value, list):
            return value
        if not value:
            raise ValueError("ALLOWED_CORS_ORIGINS must not be empty")

        text = str(value).strip()
        parsed = [item.strip() for item in text.split(",") if item.strip()]
        if not parsed:
            raise ValueError("ALLOWED_CORS_ORIGINS must include at least one origin")
        return parsed

    @field_validator("ALLOWED_CORS_ORIGINS_RAW")
    @classmethod
    def validate_allowed_origins_raw(cls, value):
        cls._parse_allowed_origins(value)
        return value

    @field_validator("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY")
    @classmethod
    def validate_jwt_secrets(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT secrets must be at least 32 characters long")
        return value

    @property
    def SECURITY_ALERT_EVENT_TYPES(self) -> List[str]:
        return self._parse_csv(self.SECURITY_ALERT_EVENT_TYPES_RAW)

    @classmethod
    def _parse_csv(cls, value: str) -> List[str]:
        text = (value or "").strip()
        if not text:
            return []
        return [item.strip() for item in text.split(",") if item.strip()]


settings = Settings()
