from __future__ import annotations

import json
import logging
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.audit_repository import AuditRepository
from app.services.email_service import EmailDeliveryError, send_email

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {"low": 10, "medium": 20, "high": 30, "critical": 40}


def _should_emit(severity: str) -> bool:
    configured = (settings.ALERT_MIN_SEVERITY or "medium").lower().strip()
    severity_rank = _SEVERITY_RANK.get(severity.lower().strip(), 0)
    min_rank = _SEVERITY_RANK.get(configured, 20)
    return severity_rank >= min_rank


def _resolve_webhook_format(url: str) -> str:
    configured = (settings.ALERT_WEBHOOK_FORMAT or "auto").lower().strip()
    if configured in {"slack", "discord"}:
        return configured
    normalized_url = (url or "").lower()
    if "discord.com/api/webhooks" in normalized_url or "discordapp.com/api/webhooks" in normalized_url:
        return "discord"
    return "slack"


def _build_webhook_payload(
    *,
    webhook_format: str,
    alert_type: str,
    severity: str,
    user_id: Optional[UUID],
    ip_address: Optional[str],
    user_agent: Optional[str],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    summary = f"[{severity.upper()}] {alert_type}"
    body_lines = [
        f"Alert: {alert_type}",
        f"Severity: {severity}",
        f"User ID: {str(user_id) if user_id else 'unknown'}",
        f"IP: {ip_address or 'unknown'}",
        f"User-Agent: {user_agent or 'unknown'}",
        f"Metadata: {json.dumps(metadata, default=str)}",
    ]
    body_text = "\n".join(body_lines)

    if webhook_format == "discord":
        color = {
            "low": 5763719,
            "medium": 15844367,
            "high": 15158332,
            "critical": 10038562,
        }.get(severity.lower(), 15844367)
        return {
            "content": summary,
            "embeds": [
                {
                    "title": "LogOnService Security Alert",
                    "description": body_text,
                    "color": color,
                    "fields": [
                        {"name": "alert_type", "value": alert_type, "inline": True},
                        {"name": "severity", "value": severity, "inline": True},
                    ],
                }
            ],
        }

    # Slack Incoming Webhooks format
    return {
        "text": summary,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "LogOnService Security Alert"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{summary}*"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{body_text}```"},
            },
        ],
    }


async def emit_security_alert(
    *,
    db: AsyncSession,
    alert_type: str,
    severity: str,
    user_id: Optional[UUID],
    metadata: dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    if not _should_emit(severity):
        return

    await AuditRepository(db).create_event(
        user_id=user_id,
        event_type="SECURITY_ALERT",
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "alert_type": alert_type,
            "severity": severity,
            **metadata,
        },
    )

    logger.warning(
        "security_alert alert_type=%s severity=%s user_id=%s ip=%s metadata=%s",
        alert_type,
        severity,
        str(user_id) if user_id else None,
        ip_address,
        json.dumps(metadata, default=str),
    )

    if settings.ALERT_EMAIL_TO:
        try:
            await send_email(
                to_email=settings.ALERT_EMAIL_TO,
                subject=f"[LogOnService][{severity.upper()}] {alert_type}",
                body_text=json.dumps(
                    {
                        "alert_type": alert_type,
                        "severity": severity,
                        "user_id": str(user_id) if user_id else None,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "metadata": metadata,
                    },
                    indent=2,
                    default=str,
                ),
            )
        except EmailDeliveryError:
            # Alerts must not block auth traffic.
            pass

    if not settings.ALERT_WEBHOOK_URL:
        return

    try:
        webhook_format = _resolve_webhook_format(settings.ALERT_WEBHOOK_URL)
        payload = _build_webhook_payload(
            webhook_format=webhook_format,
            alert_type=alert_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
        async with httpx.AsyncClient(timeout=settings.ALERT_WEBHOOK_TIMEOUT_SECONDS) as client:
            await client.post(
                settings.ALERT_WEBHOOK_URL,
                json=payload,
            )
    except Exception:
        # Alerts must not block auth traffic.
        return
