from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.translation import gettext as _

from oioioi.contests.models import Contest, Round, Submission, SubmissionReport


class Command(BaseCommand):
    help = _("Display differences between active and last hidden report for each submission")

    def add_arguments(self, parser):
        parser.add_argument(
            "-r",
            "--round",
            action="store",
            type=int,
            dest="round_id",
            help="Export only from this round",
        )
        parser.add_argument(
            "-c",
            "--contest",
            action="store",
            type=str,
            dest="contest_id",
            help="Export only from this contest",
        )
        parser.add_argument(
            "-a",
            "--all",
            action="store_false",
            default=True,
            dest="only_final",
            help="Check scored submissions, not only final.",
        )

    def handle(self, *args, **options):
        q_expressions = Q(user__isnull=False)

        if options["contest_id"]:
            contest = Contest.objects.get(id=options["contest_id"])
            q_expressions &= Q(problem_instance__contest=contest)
        if options["round_id"]:
            round = Round.objects.get(id=options["round_id"])
            q_expressions &= Q(problem_instance__round=round)
        if options["only_final"]:
            q_expressions &= Q(submissionreport__userresultforproblem__isnull=False)

        subs = Submission.objects.all()
        subs = subs.filter(q_expressions).select_related()

        for s in subs:
            reports = s.submissionreport_set
            try:
                old_report = reports.get(kind="NORMAL", status="ACTIVE")
                new_report = reports.filter(kind="HIDDEN").latest()
            except SubmissionReport.DoesNotExist:
                continue

            old_score = old_report.score_report.score
            new_score = new_report.score_report.score

            if old_score != new_score:
                print(f"{s}: {old_score} -> {new_score}")
