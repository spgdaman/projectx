from core.models import Subscription
from django.utils import timezone
from core.constants import SUBSCRIPTION_DURATION

FREE_TIER_LIMIT = 3


def can_create_subscription(user) -> bool:
    """
    Paid users have no subscription limit.
    Free-tier users are capped at FREE_TIER_LIMIT active subscriptions.
    """
    try:
        if not user.userprofile.is_free_tier:
            return True
    except Exception:
        pass

    active_count = Subscription.objects.filter(user=user, is_active=True).count()
    return active_count < FREE_TIER_LIMIT


def deactivate_subscription(subscription):
    subscription.is_active = False
    subscription.save(update_fields=["is_active", "last_updated_at"])


def update_product_subscription(subscription, new_product):
    subscription.product = new_product
    # Do NOT set category directly — the model save() override handles this
    # based on target_type='product'. Let the model enforce its own invariants.
    subscription.last_updated_at = timezone.now()
    subscription.save()


def expire_subscriptions():
    Subscription.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True,
    ).update(is_active=False)


def extend_user_subscription(user):
    """
    Extends or initialises expiry for ALL user subscriptions.
    Returns the final expiry datetime applied.
    """
    now = timezone.now()
    subscriptions = user.subscription_set.all()

    if not subscriptions.exists():
        return None

    latest_expiry = max(
        (s.expires_at for s in subscriptions if s.expires_at),
        default=None,
    )

    if latest_expiry and latest_expiry > now:
        new_expiry = latest_expiry + SUBSCRIPTION_DURATION
    else:
        new_expiry = now + SUBSCRIPTION_DURATION

    subscriptions.update(expires_at=new_expiry)
    return new_expiry
