import csv
import os

import six
import six.moves.urllib.request
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils.translation import gettext as _

from oioioi.balloons.models import BalloonsDisplay
from oioioi.contests.models import Contest


class Command(BaseCommand):
    COLUMNS = ['username', 'ip_addr']
    columns_str = ', '.join(COLUMNS)

    help = _(
        "Updates the list of balloons displays of <contest_id> from the "
        "given CSV file <filename or url>, with the following columns: "
        "%(columns)s.\n\n"
        "Given CSV file should contain a header row with column names "
        "(respectively %(columns)s) separated by commas."
    ) % {'columns': columns_str}

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument('contest_id', type=str, help='Contest id')
        parser.add_argument('filename_or_url', type=str, help='Given CSV file')

    def handle(self, *args, **options):
        try:
            contest = Contest.objects.get(id=options['contest_id'])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % options['contest_id'])

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
            raise CommandError(
                _(
                    "Missing header or invalid columns: "
                    "%(header)s\nExpected: %(expected)s"
                )
                % {'header': ', '.join(header), 'expected': ', '.join(self.COLUMNS)}
            )

        with transaction.atomic():
            BalloonsDisplay.objects.filter(contest=contest).delete()

            ok = True
            all_count = 0
            for row in reader:
                all_count += 1

                for i, _column in enumerate(self.COLUMNS):
                    row[i] = row[i].decode('utf8')

                try:
                    user = User.objects.get(username=row[0])
                    display = BalloonsDisplay(
                        ip_addr=row[1], user=user, contest=contest
                    )
                    display.save()
                except User.DoesNotExist:
                    self.stdout.write(
                        _("Error for user=%(user)s: user does not exist\n")
                        % {'user': row[1]}
                    )
                    ok = False
                except DatabaseError as e:
                    # This assumes that we'll get the message in this
                    # encoding. It is not perfect, but much better than
                    # ascii.
                    message = e.message.decode('utf-8')
                    self.stdout.write(
                        _("DB Error for user=%(user)s: %(message)s\n")
                        % {'user': row[1], 'message': message}
                    )
                    ok = False
                except ValidationError as e:
                    for k, v in six.iteritems(e.message_dict):
                        for message in v:
                            if k == '__all__':
                                self.stdout.write(
                                    _("Error for user=%(user)s: %s\n")
                                    % (row[1], message)
                                )
                            else:
                                self.stdout.write(
                                    _(
                                        "Error for user=%(user)s, "
                                        "field %(field)s: %(message)s\n"
                                    )
                                    % {'user': row[1], 'field': k, 'message': message}
                                )
                    ok = False

            if ok:
                self.stdout.write(_("Processed %d entries") % (all_count))
            else:
                raise CommandError(
                    _("There were some errors. Database not changed.\n")
                )
