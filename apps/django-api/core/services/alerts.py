from django.utils.timezone import now
from datetime import timedelta, timezone
from django.db.models import Q
from core.models import Subscription, AlertLog


def process_deal_alerts(deal):
    subscriptions = Subscription.objects.filter(
        is_active=True
    ).filter(
        Q(target_type="product", product=deal.product) |
        Q(target_type="category", category=deal.product.master_category) |
        Q(target_type="retailer", retailer=deal.retailer)
    )

    for sub in subscriptions:
        if not can_send_alert(sub, deal):
            continue

        notify(sub, deal)
        AlertLog.objects.create(subscription=sub, deal=deal)


def notify(subscription, deal):
    """
    Stub: plug email / WhatsApp / push here later
    """
    print(
        f"ALERT → {subscription.user} | "
        f"{deal.product.name} | {deal.current_price}"
    )

def can_send_alert(subscription, deal):
    if subscription.is_paid:
        return True

    cutoff = now() - timedelta(hours=24)

    return not AlertLog.objects.filter(
        subscription=subscription,
        deal__product=deal.product,
        sent_at__gte=cutoff
    ).exists()

def update_product_subscription(subscription, new_product):
    subscription.product = new_product
    subscription.category = new_product.master_category
    subscription.last_updated_at = timezone.now()
    subscription.save()
