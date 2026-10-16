import os

from celery.signals import setup_logging

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oioioi.default_settings")

from django.conf import settings  # noqa

app = Celery("oioioi")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings")


# Publishing waits until RabbitMQ confirms the message (for quorum queues:
# until a majority of nodes has it). Without this a message published just
# before the broker loses a node can disappear while apply_async succeeds,
# leaving the job queued forever; with it, publishing raises instead.
# Only for AMQP: other transports (e.g. sqlalchemy) reject unknown options.
@app.on_after_configure.connect
def enable_publisher_confirms(sender, **kwargs):
    conf = sender.conf
    if conf.broker_url and conf.broker_url.split("://", 1)[0] in ("amqp", "amqps", "pyamqp"):
        conf.broker_transport_options = {"confirm_publish": True, **(conf.broker_transport_options or {})}


# Make celery use django's logging configuration. Source:
# https://stackoverflow.com/questions/48289809/celery-logger-configuration
@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
