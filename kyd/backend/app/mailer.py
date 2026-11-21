"""Outgoing email over SMTP (KYD_SMTP_*). Port 465 uses implicit TLS; any other port uses STARTTLS."""
from __future__ import annotations
import smtplib
import ssl
from email.message import EmailMessage

from .config import settings


def configured() -> bool:
    s = settings()
    return bool(s.smtp_host and s.smtp_user and s.smtp_password)


def send(to: str, subject: str, text: str) -> None:
    s = settings()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.smtp_from or s.smtp_user, to, subject
    msg.set_content(text)
    ctx = ssl.create_default_context()
    if s.smtp_port == 465:
        with smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, context=ctx, timeout=20) as m:
            m.login(s.smtp_user, s.smtp_password)
            m.send_message(msg)
    else:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as m:
            m.starttls(context=ctx)
            m.login(s.smtp_user, s.smtp_password)
            m.send_message(msg)
