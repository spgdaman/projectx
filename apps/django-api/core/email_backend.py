"""
Custom Django email backend that reads SMTP configuration from the
EmailConfig DB singleton (when is_active=True), then falls back to
standard settings.py EMAIL_* env vars.
"""
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings


class DbConfigEmailBackend(EmailBackend):

    def __init__(self, **kwargs):
        from core.models import EmailConfig

        try:
            cfg = EmailConfig.get()
        except Exception:
            cfg = None

        if cfg and cfg.is_active:
            from_email = f"{cfg.from_name} <{cfg.from_email}>"
            super().__init__(
                host=cfg.smtp_host,
                port=cfg.smtp_port,
                username=cfg.smtp_username,
                password=cfg.smtp_password,
                use_tls=cfg.use_tls,
                use_ssl=cfg.use_ssl,
                fail_silently=kwargs.get('fail_silently', False),
            )
            self._from_email = from_email
        else:
            super().__init__(
                host=getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com'),
                port=getattr(settings, 'EMAIL_PORT', 587),
                username=getattr(settings, 'EMAIL_HOST_USER', ''),
                password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
                use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
                fail_silently=kwargs.get('fail_silently', False),
            )
            self._from_email = getattr(
                settings, 'DEFAULT_FROM_EMAIL', 'noreply@bargainhunters.co.ke'
            )
