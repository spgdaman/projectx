from core.models import Subscription

FREE_TIER_LIMIT = 3


def can_create_subscription(user):
    active_free = Subscription.objects.filter(
        user=user,
        is_free_tier=True,
        is_active=True
    ).count()

    return active_free < FREE_TIER_LIMIT

def deactivate_subscription(subscription):
    subscription.is_active = False
    subscription.save(update_fields=["is_active", "last_updated_at"])
