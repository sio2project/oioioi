from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oioioi.default_settings')

app = Celery('oioioi')

from django.conf import settings

CELERY_CONFIG = settings.CELERY or {}

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('oioioi.celery.celery:CELERY_CONFIG')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
