from oioioi.base.permissions import make_request_condition
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import submittable_problem_instances


def filter_testrun_problem_instances(instances):
    # Not returning new query_set because `instances` may have some cache in it
    testrun_instances = frozenset(ProblemInstance.objects.filter(pk__in=[p.pk for p in instances]).exclude(test_run_config=None))

    return [pi for pi in instances if pi in testrun_instances]


def testrun_problem_instances(request):
    """Returns submittable problem_instances with test run enabled."""
    return filter_testrun_problem_instances(submittable_problem_instances(request))


@make_request_condition
def has_any_testrun_problem(request):
    return len(testrun_problem_instances(request)) > 0
