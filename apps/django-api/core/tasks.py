"""
Celery tasks for core app — currently handles deal digest emails.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='core.tasks.send_deal_digest_daily')
def send_deal_digest_daily():
    """Send a daily deal digest to all opted-in users who have an email address."""
    from core.models import UserProfile, Deal
    from core.services.email import send_deal_digest

    since = timezone.now() - timedelta(hours=24)
    profiles = (
        UserProfile.objects
        .filter(email_digest_opt_in=True, email_digest_frequency='daily')
        .exclude(user__email='')
        .select_related('user')
    )

    # Gather top deals from the last 24 h (discount > 0, ordered by discount desc)
    deals_qs = (
        Deal.objects
        .filter(created_at__gte=since, discount_pct__gt=0)
        .select_related('product', 'retailer', 'product__master_category')
        .order_by('-discount_pct')[:20]
    )
    deals = [
        {
            'name': d.product.name,
            'retailer': d.retailer.name,
            'price': d.price,
            'old_price': d.old_price,
            'discount_pct': d.discount_pct,
            'image_url': d.product.image_url if hasattr(d.product, 'image_url') else None,
        }
        for d in deals_qs
    ]

    sent = failed = 0
    for profile in profiles:
        ok = send_deal_digest(profile.user, deals, period="today")
        if ok:
            sent += 1
        else:
            failed += 1

    logger.info("Daily digest: sent=%d failed=%d", sent, failed)
    return {'sent': sent, 'failed': failed}


@shared_task(name='core.tasks.send_deal_digest_weekly')
def send_deal_digest_weekly():
    """Send a weekly deal digest to all opted-in users who have an email address."""
    from core.models import UserProfile, Deal
    from core.services.email import send_deal_digest

    since = timezone.now() - timedelta(days=7)
    profiles = (
        UserProfile.objects
        .filter(email_digest_opt_in=True, email_digest_frequency='weekly')
        .exclude(user__email='')
        .select_related('user')
    )

    deals_qs = (
        Deal.objects
        .filter(created_at__gte=since, discount_pct__gt=0)
        .select_related('product', 'retailer', 'product__master_category')
        .order_by('-discount_pct')[:30]
    )
    deals = [
        {
            'name': d.product.name,
            'retailer': d.retailer.name,
            'price': d.price,
            'old_price': d.old_price,
            'discount_pct': d.discount_pct,
            'image_url': d.product.image_url if hasattr(d.product, 'image_url') else None,
        }
        for d in deals_qs
    ]

    sent = failed = 0
    for profile in profiles:
        ok = send_deal_digest(profile.user, deals, period="this week")
        if ok:
            sent += 1
        else:
            failed += 1

    logger.info("Weekly digest: sent=%d failed=%d", sent, failed)
    return {'sent': sent, 'failed': failed}
