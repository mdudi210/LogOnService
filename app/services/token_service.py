from datetime import datetime, timedelta, timezone

from app.core.constants import ACCESS_TOKEN_TTL_MINUTES


def build_access_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
