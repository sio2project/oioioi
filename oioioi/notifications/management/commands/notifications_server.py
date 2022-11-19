import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Runs the OIOIOI notifications server"
    requires_model_validation = False

    def add_arguments(self, parser):
        parser.add_argument(
            '-i',
            '--install',
            action='store_true',
            help="install dependencies required by the server",
        )

    def handle(self, *args, **options):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'server')
        os.chdir(path)
        if options['install']:
            os.execlp('env', 'env', 'npm', 'install')
        else:
            os.execlp(
                'env',
                'env',
                'node',
                'ns-main.js',
                '--port',
                settings.NOTIFICATIONS_SERVER_PORT.__str__(),
                '--url',
                settings.NOTIFICATIONS_OIOIOI_URL,
                '--amqp',
                settings.NOTIFICATIONS_RABBITMQ_URL,
            )
