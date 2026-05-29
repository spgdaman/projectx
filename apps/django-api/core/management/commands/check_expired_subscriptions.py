from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import UserProfile

class Command(BaseCommand):
    help = "Expire subscriptions and apply grace period"

    def handle(self, *args, **kwargs):
        now = timezone.now()

        profiles = UserProfile.objects.filter(
            payment_status=True
        )

        for profile in profiles:
            last_payment = profile.user.payment_set.filter(
                status="success"
            ).order_by("-expires_at").first()

            if last_payment and last_payment.expires_at < now:
                profile.payment_status = False
                profile.is_free_tier = True
                profile.grace_until = now + timedelta(days=3)
                profile.save()
