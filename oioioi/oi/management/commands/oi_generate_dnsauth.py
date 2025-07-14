from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext as _

from oioioi.contests.models import Contest
from oioioi.ipdnsauth.models import DnsToUser
from oioioi.ipdnsauth.utils import username_to_hostname
from oioioi.participants.admin import OnsiteRegistrationParticipantAdmin
from oioioi.participants.models import Participant


def username_to_dns_name(username):
    hostname = username_to_hostname(username)
    return "oi-%s.dasie.mimuw.edu.pl" % (hostname,)


class Command(BaseCommand):
    help = _("Updates the ipdnsauth module entries from the participants of the specified contest.")

    requires_model_validation = True

    def add_arguments(self, parser):
        parser.add_argument("contest_id", type=str)

    def handle(self, *args, **options):
        try:
            contest = Contest.objects.get(id=options["contest_id"])
        except Contest.DoesNotExist:
            raise CommandError(_("Contest %s does not exist") % options["contest_id"])

        rcontroller = contest.controller.registration_controller()
        if not issubclass(
            getattr(rcontroller, "participant_admin", None),
            OnsiteRegistrationParticipantAdmin,
        ):
            raise CommandError(_("Wrong type of contest"))

        with transaction.atomic():
            DnsToUser.objects.all().delete()
            dns_names = set()
            for participant in Participant.objects.filter(contest=contest).select_related("user"):
                user = participant.user
                dns_name = username_to_dns_name(user.username)
                if dns_name in dns_names:
                    raise CommandError(_("DNS names confilct: %s") % dns_name)
                dns_names.add(dns_name)
                DnsToUser(user=user, dns_name=dns_name).save()

        self.stdout.write(_("Processed %d entries") % (len(dns_names)))
