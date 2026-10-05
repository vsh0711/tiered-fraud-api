from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings

logger = logging.getLogger("fraud_api.email")


def send_email(*, settings: Settings, to_email: str, subject: str, text_body: str) -> None:
    """Send email via SMTP. In development without SMTP, log the body instead."""
    if not settings.smtp_host:
        if settings.environment.lower() in {"development", "dev", "local"}:
            logger.warning(
                '{"event":"email_dev_fallback","to":"%s","subject":"%s","body":%s}',
                to_email,
                subject,
                text_body.replace("\n", "\\n"),
            )
            return
        raise RuntimeError("SMTP is not configured (set FRAUD_SMTP_HOST and related vars)")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(text_body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
    logger.info('{"event":"email_sent","to":"%s","subject":"%s"}', to_email, subject)


def send_password_reset_email(*, settings: Settings, to_email: str, reset_url: str) -> None:
    subject = "Reset your Tiered Fraud Ops password"
    body = (
        "We received a request to reset your password.\n\n"
        f"Open this link to choose a new password (expires in {settings.password_reset_expire_minutes} minutes):\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    send_email(settings=settings, to_email=to_email, subject=subject, text_body=body)
