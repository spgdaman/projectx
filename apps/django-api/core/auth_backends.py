import phonenumbers
from django.contrib.auth.backends import ModelBackend
from core.models import UserProfile


def _normalise_phone(raw: str) -> str:
    """
    Convert any locally-formatted phone number to E.164.
    Falls back to the raw string if parsing fails so the DB lookup
    can still try an exact match.
    """
    if not raw:
        return raw
    try:
        parsed = phonenumbers.parse(raw.strip(), "KE")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return raw.strip()


class PhoneNumberBackend(ModelBackend):
    """
    Authenticate with phone number + password.

    Accepts both kwarg spellings that callers have used:
      authenticate(request, phone=..., password=...)
      authenticate(request, phone_number=..., password=...)
    and normalises the number to E.164 before querying.
    """

    def authenticate(self, request, phone=None, phone_number=None, password=None, **kwargs):
        raw = phone or phone_number
        if not raw or not password:
            return None

        normalised = _normalise_phone(raw)

        try:
            profile = UserProfile.objects.select_related("user").get(
                phone_number=normalised,
                is_active=True,
            )
        except UserProfile.DoesNotExist:
            return None

        user = profile.user
        if user.check_password(password) and user.is_active:
            return user

        return None
