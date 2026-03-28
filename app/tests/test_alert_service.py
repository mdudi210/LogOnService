from app.services.alert_service import _build_webhook_payload, _resolve_webhook_format


def test_webhook_format_auto_resolves_discord() -> None:
    fmt = _resolve_webhook_format("https://discord.com/api/webhooks/abc/def")
    assert fmt == "discord"


def test_webhook_format_auto_defaults_slack() -> None:
    fmt = _resolve_webhook_format("https://hooks.slack.com/services/T000/B000/XXX")
    assert fmt == "slack"


def test_build_slack_payload_template() -> None:
    payload = _build_webhook_payload(
        webhook_format="slack",
        alert_type="HIGH_RISK_LOGIN_ATTEMPT",
        severity="high",
        user_id=None,
        ip_address="1.2.3.4",
        user_agent="pytest-agent",
        metadata={"risk_score": 91},
    )
    assert "text" in payload
    assert "blocks" in payload


def test_build_discord_payload_template() -> None:
    payload = _build_webhook_payload(
        webhook_format="discord",
        alert_type="REFRESH_TOKEN_REUSE_DETECTED",
        severity="critical",
        user_id=None,
        ip_address="1.2.3.4",
        user_agent="pytest-agent",
        metadata={"jti": "abc"},
    )
    assert "content" in payload
    assert "embeds" in payload
