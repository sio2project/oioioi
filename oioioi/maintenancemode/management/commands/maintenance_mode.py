from __future__ import absolute_import

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from oioioi.maintenancemode.models import set_maintenance_mode


class Command(BaseCommand):
    help = _("Sets maintenance mode state")

    def add_arguments(self, parser):
        parser.add_argument('mode', type=str, choices=('on', 'off'), help='Mode')
        parser.add_argument('message', nargs='?', default="", type=str)

    def handle(self, *args, **options):
        state_value = options['mode']

        if state_value == 'on':
            message = options['message']
            set_maintenance_mode(True, message)
        elif state_value == 'off':
            set_maintenance_mode(False)
