import csv
import os

import six
import six.moves.urllib.request
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils.translation import ugettext_lazy as _


class Command(BaseCommand):
    COLUMNS = ['username', 'password', 'first_name', 'last_name', 'email']
    columns_str = ', '.join(COLUMNS)

    @property
    def help(self):
        return _("Creates user accounts from a CSV file <filename or url> "
                 "with the following columns: %(columns)s.\n\n Given CSV file "
                 "should contain a header row with column names "
                 "(respectively %(columns)s) separated by commas. Following "
                 "rows should contain user data.") \
                % {'columns': self.columns_str}

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument('filename_or_url',
                            type=str,
                            help='Source CSV file')

    def handle(self, *args, **options):
        arg = options['filename_or_url']

        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = six.moves.urllib.request.urlopen(arg)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: ") + arg)
            stream = open(arg, 'r')

        reader = csv.reader(stream)
        header = next(reader)
        if header != self.COLUMNS:
            raise CommandError(_("Missing header or invalid columns: "
                "%(header)s\nExpected: %(expected)s") % {
                    'header': ', '.join(header),
                    'expected': ', '.join(self.COLUMNS)})

        with transaction.atomic():
            ok = True
            all_count = 0
            for row in reader:
                all_count += 1

                kwargs = {}
                for i, column in enumerate(self.COLUMNS):
                    value = row[i].decode('utf8')
                    if not value:
                        continue
                    kwargs[column] = value

                username = kwargs['username']

                try:
                    User.objects.create_user(**kwargs)
                except DatabaseError as e:
                    # This assumes that we'll get the message in this
                    # encoding. It is not perfect, but much better than
                    # ascii.
                    message = e.message.decode('utf-8')
                    self.stdout.write(_(
                        "DB Error for user=%(user)s: %(message)s\n")
                            % {'user': username, 'message': message})
                    ok = False
                except ValidationError as e:
                    for k, v in six.iteritems(e.message_dict):
                        for message in v:
                            if k == '__all__':
                                self.stdout.write(_(
                                    "Error for user=%(user)s: %(message)s\n")
                                        % {'user': row[0], 'message': message})
                            else:
                                self.stdout.write(
                                        _("Error for user=%(user)s, "
                                            "field %(field)s: %(message)s\n")
                                        % {'user': username, 'field': k,
                                            'message': message})
                    ok = False

            if ok:
                self.stdout.write(_("Processed %d entries") % (all_count))
            else:
                raise CommandError(_("There were some errors. Database not "
                    "changed.\n"))
