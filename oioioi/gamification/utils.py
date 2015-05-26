from django.conf import settings
from django.db.models import F
from oioioi.contests.models import UserResultForProblem
from oioioi.problems.models import Problem

if 'oioioi.portals' in settings.INSTALLED_APPS:
    from oioioi.portals.utils import problems_in_tree


def get_solved_problems_by_user(user, problems=None):
    kwargs = {
        'submission_report__submission__problem_instance__contest__isnull':
            True,
        'submission_report__scorereport__score':
            F('submission_report__scorereport__max_score'),
        'user__pk': user.pk
    }

    if problems is not None:
        kwargs['submission_report__submission'
               '__problem_instance__problem__in'] = problems

    rfps = UserResultForProblem.objects.filter(**kwargs)

    kwargs = {
        'probleminstance__submission'
            '__submissionreport__userresultforproblem__in': rfps
    }

    return Problem.objects.filter(**kwargs)


def node_progress(node, user):
    """Returns a pair (solved problems in node, all problems in node)"""
    problems = problems_in_tree(node)
    solved = get_solved_problems_by_user(user, problems)
    return (solved.count(), problems.count())
