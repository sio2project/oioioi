import six

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from oioioi.contests.models import Contest, ProblemInstance, UserResultForProblem
from oioioi.rankings.models import Ranking

def updateContest(id, verbose):
    print("--- Recalculating scores in contest " + id + "\n")

    with transaction.atomic():
        try:
            contest = Contest.objects.get(id=id)
        except Exception:
            print("------ Error: contest doesn't exist!!!\n")
            return
        for prob_inst in ProblemInstance.objects.filter(contest=contest):
            print("--- Updating ", prob_inst.problem)
            for result in UserResultForProblem.objects.filter(
                problem_instance=prob_inst
            ):
                old_score = result.score
                contest.controller.update_user_result_for_problem(result)
                result.save()
                if verbose:
                    print(old_score, "-->", result.score)

    print("\n--- Invalidating ranking")
    Ranking.invalidate_contest(contest)
    print("--- Done!\n")


class Command(BaseCommand):
    help = _("Recalculate all results in contests with given ids")

    def add_arguments(self, parser):
        parser.add_argument(
            'id',
            type=str,
            default="",
            nargs="*",
            help='Contest id',
        )
        parser.add_argument(
            '-p',
            action='store_true',
            default=False,
            dest='verbose',
            help="Print result changes",
        )
        parser.add_argument(
            '-a',
            action='store_true',
            default=False,
            dest='all',
            help="Select all contests",
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        if options['all']:
            ids=Contest.objects.all().values_list('id', flat=True)
        else:
            ids=list(options['id'])
        print(ids)
        for i in ids:
            updateContest(i, verbose)
