import six

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from oioioi.contests.models import Contest, ProblemInstance, UserResultForProblem
from oioioi.rankings.models import Ranking


class Command(BaseCommand):
    help = _("Recalculate all results in a contest with given id")

    def add_arguments(self, parser):
        parser.add_argument('id', type=str, help='Contest id')
        parser.add_argument(
            '-p',
            action='store_true',
            default=False,
            dest='verbose',
            help="Print result changes",
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        id = options['id']
        print("--- Recalculating scores in contest " + id + "\n")

        with transaction.atomic():
            contest = Contest.objects.get(id=id)
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
        print("--- Done!")
