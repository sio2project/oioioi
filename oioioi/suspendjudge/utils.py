from oioioi.suspendjudge.models import SuspendedProblem


def is_suspended(problem_instance):
    try:
        return bool(problem_instance.suspended)
    except SuspendedProblem.DoesNotExist:
        return False


def is_suspended_on_init(problem_instance):
    try:
        return bool(problem_instance.suspended.suspend_init_tests)
    except SuspendedProblem.DoesNotExist:
        return False
