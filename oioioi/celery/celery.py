import os

from celery.signals import setup_logging

from celery import Celery, Task

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oioioi.default_settings")

from django.conf import settings  # noqa


class OioioiTask(Task):
    # With publisher confirms (see below) kombu waits for the broker ack
    # without a timeout by default. RabbitMQ withholds confirms e.g. while a
    # quorum queue has no majority, and tasks are often queued inside a DB
    # transaction (delay_environ), so publishing must fail instead of hanging.
    # A confirm timeout counts as a connection error, so Celery reconnects and
    # publishes again. One retry is enough to replace a dead pooled connection
    # (e.g. after a RabbitMQ node failover) and caps the wait at about twice
    # the timeout. A timed out message may still be enqueued later, so with a
    # quorum queue that lost its majority a task can be duplicated or outlive
    # a rolled back transaction.
    def apply_async(self, args=None, kwargs=None, **options):
        options.setdefault("confirm_timeout", settings.TASK_PUBLISH_CONFIRM_TIMEOUT)
        # Merged with CELERY_TASK_PUBLISH_RETRY_POLICY by Celery.
        options.setdefault("retry_policy", {"max_retries": 1})
        return super().apply_async(args, kwargs, **options)


app = Celery("oioioi", task_cls=OioioiTask)

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings")


# Publishing waits until RabbitMQ confirms the message (for quorum queues:
# until a majority of nodes has it). Without this a message published just
# before the broker loses a node can disappear while apply_async succeeds,
# leaving the job queued forever; with it, publishing raises instead (also
# when no confirm arrives in time, see OioioiTask).
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
