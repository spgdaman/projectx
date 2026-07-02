from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import dj_database_url
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-changeme")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1,10.0.2.2", cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "shopping_list",
    # Third-party
    "phonenumber_field",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
]

MIDDLEWARE = [
    "core.middleware.WebhookDebugMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "catalogue.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "catalogue.wsgi.application"
ASGI_APPLICATION = "catalogue.asgi.application"

# ---------------------------------------------------------------------------
# Database — SQLite for local dev, PostgreSQL in production via DATABASE_URL
# ---------------------------------------------------------------------------
_db_url = config("DATABASE_URL", default="")
if _db_url:
    DATABASES = {"default": dj_database_url.parse(_db_url, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# In development allow every origin so localhost port variations (3000, 3001…)
# and Expo (exp://) never cause preflight rejections.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = config(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:3000,http://localhost:8081",
        cast=Csv(),
    )
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://*.ngrok-free.app,https://*.ngrok-free.dev",
    cast=Csv(),
)

# ---------------------------------------------------------------------------
# Django Channels (WebSocket / real-time)
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_URL", default="redis://localhost:6379")],
        },
    },
}

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/1")

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Nairobi"

CELERY_BEAT_SCHEDULE = {
    # ── 08:00 EAT ──────────────────────────────────────────────────────────
    "scrape-naivas-0800":     {"task": "scrapers.tasks.scrape_naivas",          "schedule": crontab(hour=8,  minute=0), "options": {"queue": "naivas-queue"}},
    "scrape-chandarana-0800": {"task": "scrapers.tasks.scrape_chandarana",      "schedule": crontab(hour=8,  minute=0), "options": {"queue": "chandarana-queue"}},
    "scrape-quickmart-0800":  {"task": "scrapers.tasks.scrape_quickmart_all",   "schedule": crontab(hour=8,  minute=0), "options": {"queue": "default"}},

    # ── 12:00 EAT ──────────────────────────────────────────────────────────
    "scrape-naivas-1200":     {"task": "scrapers.tasks.scrape_naivas",          "schedule": crontab(hour=12, minute=0), "options": {"queue": "naivas-queue"}},
    "scrape-chandarana-1200": {"task": "scrapers.tasks.scrape_chandarana",      "schedule": crontab(hour=12, minute=0), "options": {"queue": "chandarana-queue"}},
    "scrape-quickmart-1200":  {"task": "scrapers.tasks.scrape_quickmart_all",   "schedule": crontab(hour=12, minute=0), "options": {"queue": "default"}},

    # ── 20:00 EAT ──────────────────────────────────────────────────────────
    "scrape-naivas-2000":     {"task": "scrapers.tasks.scrape_naivas",          "schedule": crontab(hour=20, minute=0), "options": {"queue": "naivas-queue"}},
    "scrape-chandarana-2000": {"task": "scrapers.tasks.scrape_chandarana",      "schedule": crontab(hour=20, minute=0), "options": {"queue": "chandarana-queue"}},
    "scrape-quickmart-2000":  {"task": "scrapers.tasks.scrape_quickmart_all",   "schedule": crontab(hour=20, minute=0), "options": {"queue": "default"}},

    # ── Email digests ───────────────────────────────────────────────────────
    "email-digest-daily":  {"task": "core.tasks.send_deal_digest_daily",  "schedule": crontab(hour=9, minute=0)},
    "email-digest-weekly": {"task": "core.tasks.send_deal_digest_weekly", "schedule": crontab(hour=9, minute=0, day_of_week=1)},

    # ── Oraimo — twice daily (deals refresh once/day) ───────────────────
    "scrape-oraimo-0800":  {"task": "scrapers.tasks.scrape_oraimo", "schedule": crontab(hour=8,  minute=0), "options": {"queue": "oraimo-queue"}},
    "scrape-oraimo-1600":  {"task": "scrapers.tasks.scrape_oraimo", "schedule": crontab(hour=16, minute=0), "options": {"queue": "oraimo-queue"}},

    # ── Hotpoint — twice daily (appliance prices change slowly) ─────────
    "scrape-hotpoint-0800": {"task": "scrapers.tasks.scrape_hotpoint", "schedule": crontab(hour=8,  minute=0), "options": {"queue": "hotpoint-queue"}},
    "scrape-hotpoint-2000": {"task": "scrapers.tasks.scrape_hotpoint", "schedule": crontab(hour=20, minute=0), "options": {"queue": "hotpoint-queue"}},
}

CELERY_TASK_ROUTES = {
    'scrapers.tasks.scrape_naivas':     {'queue': 'naivas-queue'},
    'scrapers.tasks.scrape_chandarana': {'queue': 'chandarana-queue'},
    'scrapers.tasks.scrape_oraimo':     {'queue': 'oraimo-queue'},
    'scrapers.tasks.scrape_hotpoint':   {'queue': 'hotpoint-queue'},
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "core.auth_backends.PhoneNumberBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Phone numbers
# ---------------------------------------------------------------------------
PHONENUMBER_DEFAULT_REGION = "KE"
PHONENUMBER_DB_FORMAT = "INTERNATIONAL"

# ---------------------------------------------------------------------------
# M-Pesa (Safaricom Daraja)
# ---------------------------------------------------------------------------
MPESA_CONSUMER_KEY = config("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = config("MPESA_CONSUMER_SECRET", default="")
MPESA_CALLBACK_URL = config("MPESA_CALLBACK_URL", default="")

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = config("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
MEDIA_URL = "/media/"
MEDIA_ROOT = config("MEDIA_ROOT", default=str(BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Proxy / HTTPS
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = False
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Shopping list
# ---------------------------------------------------------------------------
FUZZY_MATCH_THRESHOLD = 65

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.SUCCESS: "success",
    messages.ERROR: "error",
}

# ---------------------------------------------------------------------------
# Email — SMTP env-var defaults; overridden at runtime by EmailConfig DB row
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "core.email_backend.DbConfigEmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="Bargain Hunters <noreply@bargainhunters.co.ke>"
)
SITE_URL = config("SITE_URL", default="https://www.bargainhunters.co.ke")
