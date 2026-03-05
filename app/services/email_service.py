from email.message import EmailMessage
from typing import Sequence

import aiosmtplib

from app.core.config import settings


class EmailDeliveryError(Exception):
    pass


async def send_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str = "",
    cc: Sequence[str] = (),
    bcc: Sequence[str] = (),
) -> None:
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject

    if cc:
        message["Cc"] = ", ".join(cc)

    message.set_content(body_text)
    if body_html:
        message.add_alternative(body_html, subtype="html")

    recipients = [to_email, *cc, *bcc]

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=settings.SMTP_STARTTLS,
            username=settings.SMTP_USERNAME or None,
            password=settings.SMTP_PASSWORD or None,
            recipients=recipients,
        )
    except Exception as exc:
        raise EmailDeliveryError("Failed to deliver email") from exc
