# ~*~ encoding: utf-8 ~*~

from django.core.management.base import BaseCommand, CommandError

from oioioi.contests.models import Contest, Round
from oioioi.exportszu.utils import (SubmissionsWithUserDataCollector,
                                    build_submissions_archive)


class Command(BaseCommand):
    args = "contest archive_file"
    help = "Prepare archive containing similar submissions' sources."

    def add_arguments(self, parser):
        parser.add_argument('-r', '--round',
                            action='store',
                            type=int,
                            dest='round_id',
                            help="Export only from this round")
        parser.add_argument('-f', '--finished-rounds',
                            action='store_true',
                            dest='finished',
                            help="Export only from finished rounds")
        parser.add_argument('-a', '--all',
                            action='store_true',
                            dest='all',
                            help="Export all scored submissions, not only final.")

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
        with open(out_file, 'w') as f:
            build_submissions_archive(f, collector)
