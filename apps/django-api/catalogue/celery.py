import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "catalogue.settings")

app = Celery("catalogue")
app.config_from_object("django.conf:settings", namespace="CELERY")
# scrapers is not a Django app so autodiscover_tasks() (which only searches
# INSTALLED_APPS) misses it — list it explicitly so all worker queues register
# their tasks on startup.
app.autodiscover_tasks(["core", "scrapers"])
