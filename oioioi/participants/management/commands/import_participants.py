import os

import six.moves.urllib.request
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils.translation import ugettext as _

from oioioi.contests.models import Contest
from oioioi.participants.admin import ParticipantAdmin
from oioioi.participants.models import Participant


class Command(BaseCommand):
    args = _("<contest_id> <filename_or_url>")
    help = _("Updates the list of participants of <contest_id> from the given "
             "text file (one login per line).\n"
             "Lines starting with '#' are ignored.")

    requires_model_validation = True

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError(_("Expected two arguments"))

        try:
            contest = Contest.objects.get(id=args[0])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % args[0])

        rcontroller = contest.controller.registration_controller()
        if not issubclass(getattr(rcontroller, 'participant_admin', type(None)),
                          ParticipantAdmin):
            raise CommandError(_("Wrong type of contest"))

        arg = args[1]

        if arg.startswith('http://') or arg.startswith('https://'):
            self.stdout.write(_("Fetching %s...\n") % (arg,))
            stream = six.moves.urllib.request.urlopen(arg)
        else:
            if not os.path.exists(arg):
                raise CommandError(_("File not found: ") + arg)
            stream = open(arg, 'r')

        with transaction.atomic():
            ok = True
            all_count = 0
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    continue
                login = line.decode('utf8')
                all_count += 1

                try:
                    user = User.objects.get(username=login)
                    _participant, created = Participant.objects \
                            .get_or_create(contest=contest, user=user)
                except User.DoesNotExist:
                    self.stdout.write(_("Error for user=%(user)s: user does"
                        " not exist\n") % {'user': login})
                    ok = False
                except DatabaseError as e:
                    # This assumes that we'll get the message in this
                    # encoding. It is not perfect, but much better than
                    # ascii.
                    message = e.message.decode('utf-8')
                    self.stdout.write(_(
                        "DB Error for user=%(user)s: %(message)s\n")
                            % {'user': login, 'message': message})
                    ok = False
            if ok:
                self.stdout.write(_("Processed %d entries") % (all_count))
            else:
                raise CommandError(_("There were some errors. Database not "
                    "changed.\n"))
