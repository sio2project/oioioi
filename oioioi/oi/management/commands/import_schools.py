# ~*~ coding: utf-8 ~*~
import os
import string
import urllib2

import unicodecsv
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import ugettext as _

from oioioi.oi.models import School

COLUMNS = ['name', 'address', 'postal_code', 'city',
           'province', 'phone', 'email']


class Command(BaseCommand):
    columns_str = ', '.join(COLUMNS)

    args = _("filename_or_url")
    help = _("Updates the list of schools from the given CSV file "
             "<filename or url>, with the following columns: %(columns)s.\n\n"
             "Given csv file should contain a header row with columns' names "
             "(respectively %(columns)s) separeted by commas. Following rows "
             "should contain schools data.") % {'columns': columns_str}

    requires_model_validation = True

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError(_("Expected one argument - filename or url"))

        arg = args[0]

        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = urllib2.urlopen(arg)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: ") + arg)
            stream = open(arg, 'r')

        reader = unicodecsv.DictReader(stream)
        fields = reader.fieldnames
        if fields != COLUMNS:
            raise CommandError(
                _("Missing header or invalid columns: %(h)s."
                  " Expected: %(col)s")
                % {'h': ', '.join(fields), 'col': ', '.join(COLUMNS)})

        with transaction.atomic():
            ok = True
            all_count = 0
            created_count = 0
            for row in reader:
                all_count += 1

                row['address'] = row['address'].replace('ul.', '')
                row['address'] = row['address'].strip(' ')
                row['address'] = string.capwords(row['address'])

                row['postal_code'] = ''.join(row['postal_code'].split())

                for hypen in (' - ', u'\u2010'):
                    row['city'] = row['city'].replace(hypen, '-')
                row['city'] = row['city'].title()

                row['province'] = row['province'].lower()

                row['phone'] = row['phone'].split(',')[0]
                row['phone'] = row['phone'].split(';')[0]
                for c in ['tel.', 'fax.', '(', ')', '-', ' ']:
                    row['phone'] = row['phone'].replace(c, '')
                row['phone'] = row['phone'].lstrip('0')

                row['email'] = row['email'].split(',')[0]
                row['email'] = row['email'].split(';')[0]

                school, created = School.objects \
                        .get_or_create(name=row['name'],
                                       postal_code=row['postal_code'])
                if created:
                    created_count += 1

                for column in COLUMNS:
                    setattr(school, column, row[column])

                school.is_active = True
                school.is_approved = True

                try:
                    school.full_clean()
                    school.save()
                except ValidationError, e:
                    for k, v in e.message_dict.iteritems():
                        for msg in v:
                            if k == '__all__':
                                self.stdout.write(
                                    _("Line %(lineNum)s: %(msg)s\n")
                                    % {'lineNum': reader.line_num, 'msg': msg})
                            else:
                                self.stdout.write(
                                    _("Line %(lineNum)s,"
                                      " field %(field)s: %(msg)s\n")
                                    % {'lineNum': reader.line_num, 'field': k,
                                       'msg': msg})
                    ok = False

            if ok:
                self.stdout.write(
                    _("Processed %(all_count)d entries (%(new_count)d new)\n")
                    % {'all_count': all_count, 'new_count': created_count})
            else:
                raise CommandError(_("There were some errors."
                                     " Database not changed\n"))
