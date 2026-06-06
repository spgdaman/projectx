import logging

from django.core.management.base import BaseCommand
from django.db import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process deal alerts for active subscriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours', type=int, default=24,
            help='Only alert on deals scraped within this many hours (default 24)')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be sent without sending or logging anything')

    def handle(self, *args, **options):
        from django.utils import timezone
        from datetime import timedelta
        from core.models import Deal, Subscription, AlertLog
        from core.services.alert_resolver import resolve_alert_products
        from core.services.alerts import can_send_alert, notify as send_alert

        since = timezone.now() - timedelta(hours=options['hours'])
        dry_run = options['dry_run']

        # Recent deals with a price drop or new price
        recent_deals = Deal.objects.filter(
            scraped_at__gte=since,
        ).filter(
            models.Q(old_price__isnull=True) |
            models.Q(current_price__lt=models.F('old_price'))
        ).select_related(
            'product', 'retailer',
            'product__master_category',
            'branch',
        )

        if not recent_deals.exists():
            self.stdout.write('No recent deals found.')
            return

        # {(subscription_id, deal_id)} sent within the lookback window
        sent_pairs = set(
            AlertLog.objects.filter(
                sent_at__gte=since,
            ).values_list('subscription_id', 'deal_id')
        )

        subscriptions = Subscription.objects.filter(
            is_active=True,
        ).select_related(
            'user', 'user__userprofile',
            'product', 'category', 'retailer',
        )

        sent_count = 0
        skip_count = 0
        error_count = 0
        new_logs = []

        for sub in subscriptions:
            try:
                relevant = resolve_alert_products(sub)
            except Exception as exc:
                logger.error(
                    'resolve_alert_products failed for sub %d: %s', sub.id, exc)
                error_count += 1
                continue

            for deal in recent_deals:
                if deal.product not in relevant:
                    continue
                if (sub.id, deal.id) in sent_pairs:
                    skip_count += 1
                    continue
                if not can_send_alert(sub, deal):
                    skip_count += 1
                    continue

                if not dry_run:
                    try:
                        send_alert(sub, deal)
                        new_logs.append(AlertLog(
                            subscription=sub,
                            deal=deal))
                        sent_pairs.add((sub.id, deal.id))
                        sent_count += 1
                    except Exception as exc:
                        logger.error(
                            'send_alert failed sub=%d deal=%d: %s',
                            sub.id, deal.id, exc)
                        error_count += 1
                else:
                    self.stdout.write(
                        f'[DRY RUN] Would alert: '
                        f'sub={sub.id} '
                        f'deal={deal.id} '
                        f'product={deal.product.name[:30]}')
                    sent_count += 1

        if new_logs and not dry_run:
            AlertLog.objects.bulk_create(new_logs, ignore_conflicts=True)

        self.stdout.write(
            f'Alerts: sent={sent_count} '
            f'skipped={skip_count} '
            f'errors={error_count}')
