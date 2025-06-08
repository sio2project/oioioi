import os
import csv
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext as _

from oioioi.oi.models import School


class Command(BaseCommand):
    help = _(
        "Inserts School objects into the database from a CSV file or URL. "
        "Expected header: name,address,postal_code,city,province,phone,email\n"
        "Lines starting with '#' are ignored."
    )

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument('filename_or_url', type=str, help='CSV file or URL')

    def handle(self, *args, **options):
        arg = options['filename_or_url']

        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = urllib.request.urlopen(arg)
            lines = (line.decode('utf-8') for line in stream)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: %s") % arg)
            with open(arg, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        reader = csv.DictReader(
            (line for line in lines if line.strip() and not line.strip().startswith('#'))
        )

        with transaction.atomic():
            all_count = 0
            inserted_count = 0
            ok = True
            for row in reader:
                all_count += 1
                try:
                    school, created = School.objects.get_or_create(
                        name=row['name'].strip(),
                        postal_code=row['postal_code'].strip(),
                        defaults={
                            'address': row['address'].strip(),
                            'city': row['city'].strip(),
                            'province': row['province'].strip(),
                            'phone': row['phone'].strip(),
                            'email': row['email'].strip(),
                            'is_active': True,
                            'is_approved': True,
                        }
                    )
                    if created:
                        inserted_count += 1
                except DatabaseError as e:
                    message = str(e)
                    self.stdout.write(
                        _("DB Error for school=%(name)s: %(message)s\n")
                        % {'name': row.get('name', 'UNKNOWN'), 'message': message}
                    )
                    ok = False
                except Exception as e:
                    self.stdout.write(
                        _("Error for row=%(row)s: %(message)s\n")
                        % {'row': row, 'message': str(e)}
                    )
                    ok = False

            if ok:
                self.stdout.write(_("Inserted %d new schools (of %d total)") % (inserted_count, all_count))
            else:
                raise CommandError(_("There were some errors. Database not changed.\n"))
