# django_diplom/celery.py

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_diplom.settings")
app = Celery("django_diplom")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()