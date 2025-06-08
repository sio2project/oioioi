from django.core.management.base import BaseCommand, CommandError
from oioioi.contests.models import Contest
from oioioi.participants.models import Participant
from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = _("Removes all participants for the specified contest.")

    def add_arguments(self, parser):
        parser.add_argument('contest_id', type=str, help='Contest ID to clear participants from')

    def handle(self, *args, **options):
        contest_id = options['contest_id']

        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            raise CommandError(_("Contest with ID %s does not exist.") % contest_id)

        participants = Participant.objects.filter(contest=contest)
        count = participants.count()

        if count == 0:
            self.stdout.write(_("No participants found for contest ID %s.") % contest_id)
            return

        participants.delete()
        self.stdout.write(_("Deleted %d participant(s) from contest ID %s.") % (count, contest_id))
