import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catalogue.settings")
# Playwright (and other tools that start an asyncio event loop internally) cause
# Django's async-safety guard to fire even though we're in a Celery worker that
# manages its own concurrency. Allow sync ORM calls from those pseudo-async contexts.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

app = Celery("catalogue")
app.config_from_object("django.conf:settings", namespace="CELERY")
# scrapers is not a Django app so autodiscover_tasks() (which only searches
# INSTALLED_APPS) misses it — list it explicitly so all worker queues register
# their tasks on startup.
app.autodiscover_tasks(["core", "scrapers"])
