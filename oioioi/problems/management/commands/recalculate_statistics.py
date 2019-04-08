from __future__ import print_function

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import ugettext as _, ungettext

from oioioi.contests.models import Submission
from oioioi.problems.models import Problem, ProblemStatistics, UserStatistics


class Command(BaseCommand):
    help = _("Recalculates the Problemset statistics for every problem.")

    @transaction.atomic
    def handle(self, *args, **kwargs):
        ProblemStatistics.objects.select_for_update().all().delete()

        if not settings.PROBLEM_STATISTICS_AVAILABLE:
            return

        problems = Problem.objects.all()
        print(ungettext("Recalculating statistics for %(count)d problem",
                        "Recalculating statistics for %(count)d problems",
                        len(problems)) % {
                            'count': len(problems)
                        })
        for i, problem in enumerate(problems):
            print(u"{}/{}: ({}) {} - {}"
                          .format(i+1,
                                  len(problems),
                                  problem.id,
                                  problem.short_name,
                                  problem.name,
                                  ))
            problem_statistics = ProblemStatistics.objects \
                    .select_for_update() \
                    .create(problem=problem)

            user_submissions = {}
            problem_submissions = Submission.objects.\
                    filter(problem_instance__problem=problem)
            print(ungettext("\t%(count)d submission",
                            "\t%(count)d submissions",
                            len(problem_submissions)) % {
                                'count': len(problem_submissions)
                            })
            for submission in problem_submissions:
                if submission.user:
                    if submission.user not in user_submissions:
                        user_submissions[submission.user] = []
                    user_submissions[submission.user].append(submission)

            print(ungettext("\tfrom %(count)d user",
                            "\tfrom %(count)d users",
                            len(user_submissions)) % {
                                'count': len(user_submissions)
                            })
            for user, submissions in user_submissions.items():
                user_statistics = \
                    UserStatistics(user=user,
                                   problem_statistics=problem_statistics)
                for submission in submissions:
                    submission.problem_instance.controller \
                        .update_problem_statistics(problem_statistics,
                                                   user_statistics,
                                                   submission)
                user_statistics.save()
            problem_statistics.save()
        print(_("Recalculated!"))
