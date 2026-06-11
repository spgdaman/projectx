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
    user = subscription.user
    print(f"ALERT → {user} | {deal.product.name} | {deal.current_price}")

    if not user.email:
        return

    from django.conf import settings
    from core.services.email import _send

    if subscription.target_type == "product":
        sub_label = deal.product.name
    elif subscription.target_type == "category" and subscription.category:
        sub_label = subscription.category.name
    else:
        sub_label = subscription.retailer.name if subscription.retailer else "a retailer"

    _send(
        subject=f"Price drop: {deal.product.name} — KES {deal.current_price}",
        template="emails/deal_alert.html",
        context={
            "name": user.first_name or user.username,
            "deal": {
                "name": deal.product.name,
                "retailer": deal.retailer.name,
                "price": deal.current_price,
                "old_price": deal.old_price,
                "discount_pct": int((deal.old_price - deal.current_price) / deal.old_price * 100)
                    if deal.old_price and deal.old_price > deal.current_price else None,
                "image_url": getattr(deal.product, "image_url", None),
                "branch": deal.branch.name if getattr(deal, "branch", None) else None,
            },
            "subscription_type": subscription.target_type,
            "subscription_label": sub_label,
            "site_url": getattr(settings, "SITE_URL", "https://www.bargainhunters.co.ke"),
        },
        to=user.email,
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
