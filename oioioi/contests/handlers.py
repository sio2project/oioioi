import json
import logging
import pprint
import socket
import time
import traceback
from functools import wraps
from smtplib import SMTPException

from django.core.mail import mail_admins
from django.db import transaction
from six.moves import range

from oioioi.base.utils.db import require_transaction
from oioioi.contests.models import (FailureReport, ProblemInstance, Submission,
                                    SubmissionReport)
from oioioi.problems.models import ProblemStatistics, UserStatistics

logger = logging.getLogger(__name__)


WAIT_FOR_SUBMISSION_RETRIES = 9
WAIT_FOR_SUBMISSION_SLEEP_SECONDS = 1


#   TODO: Improve after migration to Python 3:
#   def _get_submission_or_skip(*args, submission_class=Submission)
def _get_submission_or_skip(*args, **kwargs):
    submission_class = kwargs.get('submission_class', Submission)

    def wrapper(fn):
        """A decorator which tries to get a submission by id from env or skips
           the decorated function if the submission doesn't exist.
        """
        @wraps(fn)
        @require_transaction
        def decorated(env, *args, **kwargs):
            if 'submission_id' not in env:
                return env
            try:
                submission = submission_class.objects.get(
                        id=env['submission_id'])
            except Submission.DoesNotExist:
                return env
            return fn(env, submission, *args, **kwargs)
        return decorated

    if len(args) == 1:
        return wrapper(args[0])
    return wrapper


def wait_for_submission_in_db(env, **kwargs):
    """Celery may start handling a submission before it is actually saved
       in the DB. This is a workaround for this.
    """
    for _i in range(WAIT_FOR_SUBMISSION_RETRIES):
        with transaction.atomic():
            if bool(Submission.objects.filter(id=env['submission_id'])):
                break
        time.sleep(WAIT_FOR_SUBMISSION_SLEEP_SECONDS)
    return env


@transaction.atomic
@_get_submission_or_skip
def update_report_statuses(env, submission, **kwargs):
    problem_instance = submission.problem_instance
    reports = SubmissionReport.objects.filter(submission=submission)
    problem_instance.controller.update_report_statuses(submission, reports)
    return env


@transaction.atomic
@_get_submission_or_skip
def update_submission_score(env, submission, **kwargs):
    problem_instance = submission.problem_instance
    problem_instance.controller.update_submission_score(submission)
    return env


def update_user_results(env, **kwargs):
    with transaction.atomic():
        try:
            submission = Submission.objects.get(id=env['submission_id'])
        except Submission.DoesNotExist:
            return env

        user = submission.user
        if not user:
            return env
        problem_instance = \
                ProblemInstance.objects.get(id=env['problem_instance_id'])
        round = problem_instance.round
        contest = None
        if round is not None:
            assert round.id == env['round_id']
            contest = round.contest
            assert contest.id == env['contest_id']
        else:
            assert 'round_id' not in env
            assert 'contest_id' not in env

    problem_instance.controller.update_user_results(user, problem_instance)

    return env


@transaction.atomic
@_get_submission_or_skip
def update_problem_statistics(env, submission, **kwargs):
    problem_statistics, created = ProblemStatistics.objects \
            .select_for_update() \
            .get_or_create(problem=submission.problem_instance.problem)

    user_statistics, created = UserStatistics.objects \
            .select_for_update() \
            .get_or_create(user=submission.user,
                           problem_statistics=problem_statistics)

    submission.problem_instance.controller \
            .update_problem_statistics(problem_statistics, user_statistics,
                                       submission)

    user_statistics.save()
    problem_statistics.save()
    return env


@transaction.atomic
@_get_submission_or_skip
def call_submission_judged(env, submission, **kwargs):
    contest = submission.problem_instance.contest

    if contest is None:
        assert 'contest_id' not in env
        return env

    assert contest.id == env['contest_id']
    contest.controller.submission_judged(submission,
            rejudged=env['is_rejudge'])
    return env


@transaction.atomic
@_get_submission_or_skip
def create_error_report(env, submission, exc_info, **kwargs):
    """Builds a :class:`oioioi.contests.models.SubmissionReport` for
       an evaulation which have failed.

       USES
           * `env['submission_id']`
    """

    logger.error("System Error evaluating submission #%s:\n%s",
            env.get('submission_id', '???'),
            pprint.pformat(env, indent=4), exc_info=exc_info)

    submission_report = SubmissionReport(submission=submission)
    submission_report.kind = 'FAILURE'
    submission_report.save()

    failure_report = FailureReport(submission_report=submission_report)
    failure_report.json_environ = json.dumps(env)
    failure_report.message = u''.join(traceback.format_exception(*exc_info))
    failure_report.save()

    return env


@transaction.atomic
@_get_submission_or_skip
def mail_admins_on_error(env, submission, exc_info, **kwargs):
    """Sends email to all admins defined in settings.ADMINS on each
       grading error occurrence.

       USES
           * `env['submission_id']`
    """

    try:
        mail_admins("System Error evaluating submission #%s" %
                    env.get('submission_id', '???'),
                    u''.join(traceback.format_exception(*exc_info)))
    except (socket.error, SMTPException) as e:
        logger.error("An error occurred while sending email: %s",
                     e.message)

    return env
