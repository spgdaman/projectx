"""
Email service — all outgoing email goes through these helpers so that
template rendering, from-address, and error handling are centralised.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

if TYPE_CHECKING:
    from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def _get_from_address() -> str:
    from core.models import EmailConfig
    try:
        cfg = EmailConfig.get()
        if cfg.is_active:
            return f"{cfg.from_name} <{cfg.from_email}>"
    except Exception:
        pass
    return getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bargainhunters.co.ke')


def _send(subject: str, template: str, context: dict, to: str) -> bool:
    """Render template, send HTML+text email. Returns True on success."""
    try:
        from_addr = _get_from_address()
        html_body = render_to_string(template, context)
        text_body = strip_tags(html_body)
        msg = EmailMultiAlternatives(subject, text_body, from_addr, [to])
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        return True
    except Exception as exc:
        logger.error("Email send failed to %s: %s", to, exc, exc_info=True)
        return False


def send_welcome_email(user: User) -> bool:
    email = user.email
    if not email:
        return False
    name = user.first_name or user.username
    return _send(
        subject="Welcome to Bargain Hunters!",
        template="emails/welcome.html",
        context={
            "name": name,
            "site_url": getattr(settings, 'SITE_URL', 'https://www.bargainhunters.co.ke'),
        },
        to=email,
    )


def send_payment_receipt(user: User, amount: str, reference: str) -> bool:
    email = user.email
    if not email:
        return False
    name = user.first_name or user.username
    return _send(
        subject="Payment Receipt — Bargain Hunters Premium",
        template="emails/payment_receipt.html",
        context={
            "name": name,
            "amount": amount,
            "reference": reference,
            "site_url": getattr(settings, 'SITE_URL', 'https://www.bargainhunters.co.ke'),
        },
        to=email,
    )


def send_deal_digest(user: User, deals: list, period: str = "today") -> bool:
    email = user.email
    if not email:
        return False
    name = user.first_name or user.username
    return _send(
        subject=f"Your deal digest — {period}'s best bargains",
        template="emails/deal_digest.html",
        context={
            "name": name,
            "deals": deals,
            "period": period,
            "site_url": getattr(settings, 'SITE_URL', 'https://www.bargainhunters.co.ke'),
        },
        to=email,
    )


def send_test_email(to: str) -> bool:
    return _send(
        subject="Test email from Bargain Hunters",
        template="emails/test.html",
        context={
            "site_url": getattr(settings, 'SITE_URL', 'https://www.bargainhunters.co.ke'),
        },
        to=to,
    )
