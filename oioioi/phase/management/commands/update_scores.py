from __future__ import print_function

import six

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from oioioi.contests.models import Contest, ProblemInstance, UserResultForProblem

class Command(BaseCommand):
    help = _("Recalculate all results in a contest with given id")
    
    def add_arguments(self, parser):
        parser.add_argument('id', type=str, help='Contest id')

    def handle(self, *args, **options):
        id = options['id']
        
        contest=Contest.objects.get(id=id)
        for prob_inst in ProblemInstance.objects.filter(contest=contest):
            print("---", prob_inst.problem)
            for result in UserResultForProblem.objects.filter(problem_instance=prob_inst):
                print(result.score, end='	--> ')
                contest.controller.update_user_result_for_problem(result)
                result.save()
                print(result.score)
