from django.core.management.base import BaseCommand
from django.db.models import F
from django.utils.translation import gettext as _
from oioioi.problems.models import Problem
from oioioi.programs.models import ModelProgramSubmission


class Command(BaseCommand):
    help = str(
        _(
            "Prints problems without 100-scored model solution. If "
            "username is provided it shows only problems added by that "
            "user."
        )
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            metavar='USERNAME',
            help='Optional username for filtering problems.',
        )

    def handle(self, *args, **options):
        username = options.get('user')

        problems = self.get_problems_without_correct_modelsolution(username)
        self.stdout.write('Problems: ' + str(len(problems)) + '\n')
        for problem in problems:
            message = u'- {name} / {short_name} ; id = {id}\n'.format(
                name=problem.name, short_name=problem.short_name, id=str(problem.pk)
            )
            self.stdout.write(message)

    def get_problems_without_correct_modelsolution(self, username=None):
        if username is not None:
            problems = Problem.objects.filter(author__username=username)
        else:
            problems = Problem.objects.all()
        bad_problems = []
        for problem in problems:
            correct_model_submissions = ModelProgramSubmission.objects.filter(
                score=F('submissionreport__scorereport__max_score'),
                model_solution__problem=problem,
            ).order_by('id')
            if not correct_model_submissions:
                bad_problems.append(problem)
        return bad_problems
