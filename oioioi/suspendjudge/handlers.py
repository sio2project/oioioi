from celery.exceptions import Ignore

from oioioi.contests.models import Submission
from oioioi.programs.models import ModelProgramSubmission
from oioioi.suspendjudge.models import SuspendedProblem
from oioioi.submitsqueue.handlers import mark_submission_state


def _is_suspended(problem_instance_id, suspend_init_tests=None):
    if suspend_init_tests is None:
        return SuspendedProblem.objects.filter(
            problem_instance=problem_instance_id).exists()
    else:
        return SuspendedProblem.objects.filter(
            problem_instance=problem_instance_id,
            suspend_init_tests=suspend_init_tests).exists()


def _is_hidden_rejudge(env):
    return env['is_rejudge'] and 'HIDDEN' in env['report_kinds']


def _is_admin_submission(env):
    s = Submission.objects.get(pk=env['submission_id'])
    if s.user is not None:
        return s.user.has_perm('contests.contest_admin',
                               s.problem_instance.contest)
    return False


def _is_model_solution(env):
    if ModelProgramSubmission.objects.filter(pk=env['submission_id']).exists():
        return True
    else:
        return False


def check_problem_instance_state(env, suspend_init_tests=None, **kwargs):
    if _is_suspended(env['problem_instance_id'], suspend_init_tests) and not \
            _is_hidden_rejudge(env) and not _is_admin_submission(env) and not \
            _is_model_solution(env):
        mark_submission_state(env, 'SUSPENDED', **kwargs)
        raise Ignore

    return env
