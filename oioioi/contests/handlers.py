import json
import logging
import traceback
import pprint
import socket
from smtplib import SMTPException
from django.core.mail import mail_admins
from django.db import transaction
from oioioi.contests.models import Contest, ProblemInstance, Submission, \
        SubmissionReport, FailureReport

logger = logging.getLogger(__name__)


@transaction.commit_on_success
def update_report_statuses(env, **kwargs):
    contest = Contest.objects.get(id=env['contest_id'])
    submission = Submission.objects.get(id=env['submission_id'])
    reports = SubmissionReport.objects.filter(submission=submission)
    contest.controller.update_report_statuses(submission, reports)
    return env


@transaction.commit_on_success
def update_submission_score(env, **kwargs):
    contest = Contest.objects.get(id=env['contest_id'])
    submission = Submission.objects.get(id=env['submission_id'])
    contest.controller.update_submission_score(submission)
    return env


def update_user_results(env, **kwargs):
    with transaction.commit_on_success():
        submission = Submission.objects.get(id=env['submission_id'])
        user = submission.user
        if not user:
            return env
        problem_instance = \
                ProblemInstance.objects.get(id=env['problem_instance_id'])
        round = problem_instance.round
        assert round.id == env['round_id']
        contest = round.contest
        assert contest.id == env['contest_id']

    contest.controller.update_user_results(user, problem_instance)

    return env


@transaction.commit_on_success
def call_submission_judged(env, **kwargs):
    contest = Contest.objects.get(id=env['contest_id'])
    submission = Submission.objects.get(id=env['submission_id'])
    contest.controller.submission_judged(submission)
    return env


@transaction.commit_on_success
def create_error_report(env, exc_info, **kwargs):
    """Builds a :class:`oioioi.contests.models.SubmissionReport` for
       an evaulation which have failed.

       USES
           * `env['submission_id']`
    """

    logger.error("System Error evaluating submission #%s:\n%s",
            env.get('submission_id', '???'),
            pprint.pformat(env, indent=4), exc_info=exc_info)

    if 'submission_id' not in env:
        return env

    try:
        submission = Submission.objects.get(id=env['submission_id'])
    except Submission.DoesNotExist:
        return env

    submission_report = SubmissionReport(submission=submission)
    submission_report.kind = 'FAILURE'
    submission_report.save()

    failure_report = FailureReport(submission_report=submission_report)
    failure_report.json_environ = json.dumps(env)
    failure_report.message = traceback.format_exc(exc_info)
    failure_report.save()

    return env


def mail_admins_on_error(env, exc_info, **kwargs):
    """Sends email to all admins defined in settings.ADMINS on each
       grading error occurrence.

       USES
           * `env['submission_id']`
    """

    # We don't want to spam admins when the evaluation of a deleted
    # submission fails. See also SIO-1254.
    try:
        if 'submission_id' in env:
            Submission.objects.get(id=env['submission_id'])
    except Submission.DoesNotExist:
        return env

    try:
        mail_admins("System Error evaluating submission #%s" %
                    env.get('submission_id', '???'),
                    traceback.format_exc(exc_info))
    except (socket.error, SMTPException), e:
        logger.error("An error occurred while sending email: %s",
                     e.message)

    return env
