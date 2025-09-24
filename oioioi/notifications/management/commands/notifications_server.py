from django.conf import settings
from django.core.management.base import BaseCommand
from oioioi.notifications.server.server import Server
import asyncio


class Command(BaseCommand):
    help = "Runs the OIOIOI notifications server"
    requires_model_validation = False

    def handle(self, *args, **options):
        server = Server(settings.NOTIFICATIONS_SERVER_PORT, settings.NOTIFICATIONS_RABBITMQ_URL, settings.NOTIFICATIONS_OIOIOI_URL)
        try:
            asyncio.run(server.run())
        except KeyboardInterrupt:
            pass  # Allow graceful shutdown on Ctrl+C
