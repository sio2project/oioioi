from __future__ import absolute_import
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _

from oioioi.maintenancemode.models import set_maintenance_mode


class Command(BaseCommand):
    args = _('<on|off> "<message>"')
    help = _("Sets maintenance mode state")

    def handle(self, *args, **options):
        if len(args) == 0 or len(args) > 2:
            raise CommandError(_("Expected one or two arguments"))

        state_value = args[0].lower()
        if state_value in ['on', 'yes', 'true', '1']:
            message = ''
            if len(args) > 1:
                message = args[1]
            set_maintenance_mode(True, message)
        elif state_value in ['off', 'no', 'false', '0']:
            set_maintenance_mode(False)
        else:
            raise CommandError(_("Unrecognized first argument"))
