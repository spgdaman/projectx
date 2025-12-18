from core.models import Subscription
from django.utils import timezone
from core.constants import SUBSCRIPTION_DURATION

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

def update_product_subscription(subscription, new_product):
    subscription.product = new_product
    subscription.category = new_product.master_category
    subscription.last_updated_at = timezone.now()
    subscription.save()

def expire_subscriptions():
    Subscription.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True
    ).update(is_active=False)

# def extend_user_subscription(user):
#     """
#     Extend or initialise expiry for ALL subscriptions of a user,
#     regardless of active/inactive status.
#     """
#     now = timezone.now()

#     subscriptions = user.subscription_set.all()

#     if not subscriptions.exists():
#         return None

#     for sub in subscriptions:
#         if sub.expires_at and sub.expires_at > now:
#             # 🔁 Roll forward existing expiry
#             sub.expires_at = sub.expires_at + SUBSCRIPTION_DURATION
#         else:
#             # 🆕 Initialise / reset expiry
#             sub.expires_at = now + SUBSCRIPTION_DURATION

#         sub.save(update_fields=["expires_at"])

#     return subscriptions

def extend_user_subscription(user):
    """
    Extends or initialises expiry for ALL user subscriptions.
    Returns the final expiry datetime applied.
    """
    now = timezone.now()
    subscriptions = user.subscription_set.all()

    if not subscriptions.exists():
        return None

    # Determine base expiry (max expiry across subs)
    latest_expiry = max(
        (s.expires_at for s in subscriptions if s.expires_at),
        default=None
    )

    if latest_expiry and latest_expiry > now:
        new_expiry = latest_expiry + SUBSCRIPTION_DURATION
    else:
        new_expiry = now + SUBSCRIPTION_DURATION

    # Apply same expiry to all subscriptions
    subscriptions.update(expires_at=new_expiry)

    return new_expiry
