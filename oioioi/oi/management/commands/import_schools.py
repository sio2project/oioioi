from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.db import transaction
from oioioi.oi.models import School
import os
import csv
import urllib2

COLUMNS = ['id', 'name', 'address', 'postal_code', 'city',
           'province', 'phone', 'email']

class Command(BaseCommand):
    columns_str = ', '.join(COLUMNS)

    DEFAULT_URL = 'https://docs.google.com/spreadsheet/pub?key=' + \
                  '0Ar_qj6TlD3i5dHdOcDk1UjFtV3FmYXVabVJ3bm5Mc0E&output=csv'

    args = _("[filename_or_url]")
    help = _("Updates the list of schools from the given CSV file "
             "<filename or url>, with the following columns: %s.\n\n"
             "Given csv file should contain a header row with columns' names "
             "(respectively %s) separeted by commas. Following rows should "
             "contain schools data.") % (columns_str, columns_str)

    requires_model_validation = True

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError(_("Expected no more than one argument"))

        if not args:
            arg = DEFAULT_URL
        else:
            arg = args[0]
        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = urllib2.urlopen(arg)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: ") + arg)
            stream = open(arg, 'r')

        reader = csv.reader(stream)
        header = reader.next()
        if header != COLUMNS:
            raise CommandError(_("Missing header or invalid columns: %s\n"
                "Expected: %s") % (', '.join(header), ', '.join(COLUMNS)))

        with transaction.commit_on_success():
            ok = True
            all_count = 0
            created_count = 0
            for row in reader:
                all_count += 1

                for i, column in enumerate(COLUMNS):
                    row[i] = row[i].decode('utf8')

                school, created = School.objects.get_or_create(name=row[1],
                    postal_code=row[3])

                row[0] = school.id

                if created:
                    created_count += 1
                for i, column in enumerate(COLUMNS):
                    setattr(school, column, row[i])
                try:
                    school.full_clean()
                    school.save()
                except ValidationError, e:
                    for k, v in e.message_dict.iteritems():
                        for message in v:
                            if k == '__all__':
                                self.stdout.write(_("Error in ID=%s: %s\n")
                                        % (row[0], message))
                            else:
                                self.stdout.write(
                                        _("Error in ID=%s, field %s: %s\n")
                                        % (row[0], k, message))
                    ok = False

            if ok:
                self.stdout.write(_("Processed %d entries (%d new)\n") %
                        (all_count, created_count))
            else:
                raise CommandError(_("There were some errors. Database not "
                    "changed\n"))
