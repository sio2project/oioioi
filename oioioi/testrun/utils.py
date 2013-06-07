from oioioi.base.permissions import make_request_condition
from oioioi.contests.utils import submittable_problem_instances
from oioioi.testrun.models import TestRunConfig
from oioioi.problems.models import Problem


def has_testrun(problem):
    try:
        return bool(problem.test_run_config)
    except TestRunConfig.DoesNotExist:
        return False


def filter_testrun_problem_instances(instances):
    # Not returning new query_set because `instances` may have some cache in it
    problems = frozenset(Problem.objects
            .filter(pk__in=[p.problem.pk for p in instances])
            .exclude(test_run_config=None))
    return [pi for pi in instances if pi.problem in problems]


def testrun_problem_instances(request):
    """Returns submittable problem_instances with test run enabled."""
    return filter_testrun_problem_instances(
                                        submittable_problem_instances(request))


@make_request_condition
def has_any_testrun_problem(request):
    return len(testrun_problem_instances(request)) > 0
