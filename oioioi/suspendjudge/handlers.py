from django.db import transaction

from celery.exceptions import Ignore
from oioioi.contests.handlers import _get_submission_or_skip
from oioioi.evalmgr.utils import mark_job_state
from oioioi.programs.models import ModelProgramSubmission
from oioioi.suspendjudge.models import SuspendedProblem


def _is_suspended(problem_instance_id, suspend_init_tests=None):
    if suspend_init_tests is None:
        return SuspendedProblem.objects.filter(
            problem_instance=problem_instance_id
        ).exists()
    else:
        return SuspendedProblem.objects.filter(
            problem_instance=problem_instance_id, suspend_init_tests=suspend_init_tests
        ).exists()


def _is_hidden_rejudge(env):
    return env['is_rejudge'] and 'HIDDEN' in env['report_kinds']


@_get_submission_or_skip
def _is_admin_submission(env, submission):
    if submission.user is not None:
        return submission.user.has_perm(
            'contests.contest_admin', submission.problem_instance.contest
        )
    return False


def _is_model_solution(env):
    if ModelProgramSubmission.objects.filter(pk=env['submission_id']).exists():
        return True
    else:
        return False


def check_problem_instance_state(env, suspend_init_tests=None, **kwargs):
    suspend = False
    with transaction.atomic():
        if (
            _is_suspended(env['problem_instance_id'], suspend_init_tests)
            and not _is_hidden_rejudge(env)
            and not _is_admin_submission(env)
            and not _is_model_solution(env)
        ):
            mark_job_state(env, 'SUSPENDED')
            suspend = True
    if suspend:
        raise Ignore
    return env
