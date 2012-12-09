from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from django.db import transaction, DatabaseError
from oioioi.contests.models import Contest
from oioioi.participants.models import Participant
from oioioi.oi.models import Region, OIOnsiteRegistration
from oioioi.oi.admin import OIOnsiteRegistrationParticipantAdmin
import os
import csv
import urllib2

class Command(BaseCommand):
    COLUMNS = ['number', 'username', 'region_short_name', 'local_number']
    columns_str = ', '.join(COLUMNS)

    args = _("<contest_id> <filename_or_url>")
    help = _("Updates the list of participants of <contest_id> from the given "
             "CSV file <filename or url>, with the following columns: %s.\n\n"
             "Given csv file should contain a header row with columns' names "
             "(respectively %s) separeted by commas. Following rows should "
             "contain participants data.") % (columns_str, columns_str)

    requires_model_validation = True

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError(_("Expected two arguments"))

        try:
            contest = Contest.objects.get(id=args[0])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % args[0])

        rcontroller = contest.controller.registration_controller()
        if not issubclass(getattr(rcontroller, 'participant_admin', None),
                          OIOnsiteRegistrationParticipantAdmin):
            raise CommandError(_("Wrong type of contest"))

        arg = args[1]

        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = urllib2.urlopen(arg)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: ") + arg)
            stream = open(arg, 'r')

        reader = csv.reader(stream)
        header = reader.next()
        if header != self.COLUMNS:
            raise CommandError(_("Missing header or invalid columns: %s\n"
                "Expected: %s") % (', '.join(header), ', '.join(self.COLUMNS)))

        with transaction.commit_on_success():
            ok = True
            all_count = 0
            for row in reader:
                all_count += 1

                for i, column in enumerate(self.COLUMNS):
                    row[i] = row[i].decode('utf8')

                try:
                    user = User.objects.get(username=row[1])
                    region = Region.objects.get(short_name=row[2])

                    participant, created = Participant.objects \
                            .get_or_create(contest=contest, user=user)

                    reg = OIOnsiteRegistration(participant=participant,
                            number=row[0], local_number=row[3], region=region)

                    reg.full_clean()
                    reg.save()
                except User.DoesNotExist:
                    self.stdout.write(_("Error for user=%s: user does"
                                        " not exist\n") % (row[1]))
                    ok = False
                except Region.DoesNotExist:
                    self.stdout.write(_("Error for user=%s: region %s does"
                                        " not exist\n") % (row[1], row[2]))
                    ok = False
                except DatabaseError, e:
                    self.stdout.write(_("DB Error for user=%s: %s\n")
                                      % (row[1], e.message))
                    ok = False
                except ValidationError, e:
                    for k, v in e.message_dict.iteritems():
                        for message in v:
                            if k == '__all__':
                                self.stdout.write(_("Error for user=%s: %s\n")
                                        % (row[1], message))
                            else:
                                self.stdout.write(
                                        _("Error for user=%s, field %s: %s\n")
                                        % (row[1], k, message))
                    ok = False

            if ok:
                self.stdout.write(_("Processed %d entries") % (all_count))
            else:
                raise CommandError(_("There were some errors. Database not "
                    "changed.\n"))

