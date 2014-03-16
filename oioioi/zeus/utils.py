from oioioi.base.permissions import make_request_condition
from oioioi.base.utils import request_cached
from oioioi.problems.models import Problem
from oioioi.testrun.utils import testrun_problem_instances
from oioioi.zeus.models import ZeusProblemData


def is_zeus_problem(problem):
    try:
        return bool(problem.zeusproblemdata)
    except ZeusProblemData.DoesNotExist:
        return False


def filter_zeus_problem_instances(problem_instances):
    # Not returning new query_set because `instances` may have some cache in it
    problems = frozenset(Problem.objects
            .filter(pk__in=[p.problem.pk for p in problem_instances])
            .exclude(zeusproblemdata=None))
    return [pi for pi in problem_instances if pi.problem in problems]


def zeus_testrun_problem_instances(request):
    return filter_zeus_problem_instances(testrun_problem_instances(request))


@make_request_condition
@request_cached
def has_any_zeus_testrun_problem(request):
    return len(zeus_testrun_problem_instances(request)) > 0
