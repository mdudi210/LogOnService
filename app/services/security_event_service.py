import json
import logging
from typing import Any, Optional
from uuid import UUID

from app.core.config import settings
from app.services.email_service import EmailDeliveryError, send_email

logger = logging.getLogger("app.security.events")


async def emit_security_event(
    *,
    event_type: str,
    metadata: dict[str, Any],
    user_id: Optional[UUID],
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> None:
    payload = {
        "event_type": event_type,
        "user_id": str(user_id) if user_id else None,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "metadata": metadata,
    }
    logger.warning("security_event=%s", json.dumps(payload, default=str, separators=(",", ":")))

    if not settings.SECURITY_ALERTS_ENABLED:
        return
    if event_type not in settings.SECURITY_ALERT_EVENT_TYPES:
        return
    if not settings.SECURITY_ALERT_EMAIL:
        return

    try:
        await send_email(
            to_email=settings.SECURITY_ALERT_EMAIL,
            subject=f"[LogOnService] Security alert: {event_type}",
            body_text=json.dumps(payload, indent=2, default=str),
        )
    except EmailDeliveryError:
        logger.exception("security_alert_delivery_failed event_type=%s", event_type)

