import re

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from django.db import transaction

from oioioi.contests.models import Contest
from oioioi.ipdnsauth.models import DnsToUser
from oioioi.participants.models import Participant
from oioioi.oi.admin import OIOnsiteRegistrationParticipantAdmin


def username_to_dns_name(username):
    name = re.sub(r'[^a-z0-9]', '', username.lower())
    return 'oi-%s.dasie.mimuw.edu.pl' % (name,)


class Command(BaseCommand):
    args = _("<contest_id>")
    help = _("Updates the ipdnsauth module entries from the participants of "
             "the specified contest.")

    requires_model_validation = True

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError(_("Expected one argument"))

        try:
            contest = Contest.objects.get(id=args[0])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % args[0])

        rcontroller = contest.controller.registration_controller()
        if not issubclass(getattr(rcontroller, 'participant_admin', None),
                          OIOnsiteRegistrationParticipantAdmin):
            raise CommandError(_("Wrong type of contest"))

        with transaction.atomic():
            DnsToUser.objects.all().delete()
            dns_names = set()
            for participant in Participant.objects.filter(contest=contest) \
                    .select_related('user'):
                user = participant.user
                dns_name = username_to_dns_name(user.username)
                if dns_name in dns_names:
                    raise CommandError(_("DNS names confilct: %s") % dns_name)
                dns_names.add(dns_name)
                DnsToUser(user=user, dns_name=dns_name).save()

        self.stdout.write(_("Processed %d entries") % (len(dns_names)))
