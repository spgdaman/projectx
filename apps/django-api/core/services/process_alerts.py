from django.core.management.base import BaseCommand
from core.models import Subscription, Deal
from core.services.alert_resolver import resolve_alert_products
from core.services.throttling import can_send_alert
from core.services.notifications import send_alert
from core.models import AlertLog

class Command(BaseCommand):
    help = "Process deal alerts"

    def handle(self, *args, **kwargs):
        deals = Deal.objects.all()

        for deal in deals:
            subscriptions = Subscription.objects.filter(is_active=True)

            for sub in subscriptions:
                products = resolve_alert_products(sub)

                if deal.product not in products:
                    continue

                if not can_send_alert(sub, deal):
                    continue

                send_alert(sub, deal)
                AlertLog.objects.create(subscription=sub, deal=deal)
