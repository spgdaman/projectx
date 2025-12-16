# core/auth_backends.py

from django.contrib.auth.backends import ModelBackend
from core.models import UserProfile


class PhoneNumberBackend(ModelBackend):
    """
    Authenticate using phone number + password (or later OTP).
    """

    def authenticate(self, request, phone_number=None, password=None, **kwargs):
        if phone_number is None or password is None:
            return None

        try:
            profile = UserProfile.objects.select_related("user").get(
                phone_number=phone_number,
                is_active=True
            )
        except UserProfile.DoesNotExist:
            return None

        user = profile.user
        if user.check_password(password) and user.is_active:
            return user

        return None
