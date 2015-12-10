# ~*~ encoding: utf-8 ~*~

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from oioioi.contests.models import Contest, Round
from oioioi.exportszu.utils import SubmissionsWithUserDataCollector, \
    build_submissions_archive


class Command(BaseCommand):
    args = "contest archive_file"
    help = "Prepare archive containing similar submissions' sources."

    option_list = BaseCommand.option_list + (
        make_option('-r', '--round',
                    action='store',
                    type='int',
                    dest='round_id',
                    help="Export only from this round"),
        make_option('-f', '--finished-rounds',
                    action='store_true',
                    dest='finished',
                    help="Export only from finished rounds"),
        make_option('-a', '--all',
                    action='store_true',
                    dest='all',
                    help="Export all scored submissions, not only final."),
        )

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError("Exactly two arguments are required.")

        contest_id = args[0]
        out_file = args[1]

        contest = Contest.objects.get(id=contest_id)

        round_id = options.get('round_id')
        if round_id:
            round = Round.objects.get(id=round_id)
            if round.contest != contest:
                raise CommandError(
                    "This round doesn't belong to the chosen contest.")
        else:
            round = None

        collector = SubmissionsWithUserDataCollector(contest, round=round,
            only_final=not options.get('all'))
        build_submissions_archive(out_file, collector)
