from django.db.models import Q
from core.models import Subscription


def process_deal_alerts(deal):
    subscriptions = Subscription.objects.filter(
        is_active=True
    ).filter(
        Q(target_type="product", product=deal.product) |
        Q(target_type="category", category=deal.product.master_category) |
        Q(target_type="retailer", retailer=deal.retailer)
    )

    for sub in subscriptions:
        if sub.alert_type == "price_drop":
            if deal.old_price and deal.current_price:
                if deal.current_price < deal.old_price:
                    notify(sub, deal)
        else:
            notify(sub, deal)


def notify(subscription, deal):
    """
    Stub: plug email / WhatsApp / push here later
    """
    print(
        f"ALERT → {subscription.user} | "
        f"{deal.product.name} | {deal.current_price}"
    )
