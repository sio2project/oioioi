import os

from django.conf import settings
from django.core.management.base import BaseCommand
from oioioi.notifications.server.server import Server

class Command(BaseCommand):
    help = "Runs the OIOIOI notifications server"
    requires_model_validation = False

    def handle(self, *args, **options):
        server = Server()
        server.run()
