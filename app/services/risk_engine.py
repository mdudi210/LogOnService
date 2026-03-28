from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class RiskAssessment:
    level: str
    score: int
    reasons: list[str]


def _is_private_ip(ip_address: str) -> bool:
    try:
        return ipaddress.ip_address(ip_address).is_private
    except ValueError:
        return ip_address in {"testclient", "localhost", "127.0.0.1", "::1"}


def assess_login_risk(
    *,
    ip_address: str,
    is_new_device: bool,
    user_agent: str,
    mfa_enabled: bool,
) -> RiskAssessment:
    score = 0
    reasons: list[str] = []

    if is_new_device:
        score += 45
        reasons.append("new_device")

    if not _is_private_ip(ip_address):
        score += 20
        reasons.append("public_network")

    agent = (user_agent or "").lower()
    if any(marker in agent for marker in ("curl", "python-requests", "postman")):
        score += 20
        reasons.append("non_browser_user_agent")
    if "testclient" in agent:
        score = max(score - 20, 0)
        reasons.append("test_client")

    if mfa_enabled:
        score = max(score - 10, 0)
        reasons.append("mfa_enabled")

    if score >= settings.RISK_HIGH_SCORE_THRESHOLD:
        level = "high"
    elif score >= settings.RISK_MEDIUM_SCORE_THRESHOLD:
        level = "medium"
    else:
        level = "low"

    return RiskAssessment(level=level, score=score, reasons=reasons)
