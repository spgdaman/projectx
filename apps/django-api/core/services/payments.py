import uuid
from core.models import Payment
from django.utils import timezone
from datetime import timedelta

def activate_subscription(subscription):
    subscription.is_paid = True
    subscription.is_free_tier = False
    subscription.is_active = True
    subscription.save()

def create_payment(user, amount, provider):
    payment = Payment.objects.create(
        user=user,
        amount=amount,
        provider=provider,
        reference=str(uuid.uuid4())
    )
    return payment

def mark_payment_success(payment, provider_reference=None):
    payment.status = "success"
    payment.provider_reference = provider_reference
    payment.completed_at = timezone.now()
    payment.expires_at = timezone.now() + timedelta(days=30)
    payment.save()

    profile = payment.user.userprofile
    profile.payment_status = True
    profile.is_free_tier = False
    profile.grace_until = None
    profile.save()

def expire_stale_payments():
    Payment.objects.filter(
        status="pending",
        expires_at__lt=timezone.now()
    ).update(status="expired")
