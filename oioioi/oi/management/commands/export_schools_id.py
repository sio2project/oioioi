import csv

import sys
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from oioioi.oi.management.commands.import_schools import COLUMNS
from oioioi.oi.models import School

COLUMNS = ['id'] + COLUMNS

class Command(BaseCommand):
    help = _("Exports schools list to a CSV file")

    requires_model_validation = True

    def handle(self, *args, **options):
        writer = csv.writer(sys.stdout)
        writer.writerow(COLUMNS)
        schools = School.objects.filter(is_approved=True, is_active=True)
        for school in schools.order_by('postal_code'):
            row = [str(getattr(school, column)).encode('utf-8')
                    for column in COLUMNS]
            writer.writerow(row)
