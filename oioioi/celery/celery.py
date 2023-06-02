from __future__ import absolute_import

import os

from celery import Celery
from celery.signals import setup_logging

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oioioi.default_settings')

from django.conf import settings  # noqa

app = Celery('oioioi')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')

# Make celery use django's logging configuration. Source:
# https://stackoverflow.com/questions/48289809/celery-logger-configuration
@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
