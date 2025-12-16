from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Payment


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        expired = Payment.objects.filter(
            status="success",
            expires_at__lt=timezone.now()
        )

        for payment in expired:
            profile = payment.user.userprofile
            profile.payment_status = False
            profile.is_free_tier = True
            profile.save()
