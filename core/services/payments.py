import uuid
from core.models import Payment
from django.utils import timezone

def activate_subscription(subscription):
    subscription.is_paid = True
    subscription.is_free_tier = False
    subscription.is_active = True
    subscription.save()

def create_payment(user, amount, provider="mpesa"):
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
    payment.save()

    profile = payment.user.userprofile
    profile.payment_status = True
    profile.is_free_tier = False
    profile.save()

    