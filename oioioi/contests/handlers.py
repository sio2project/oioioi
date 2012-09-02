from django.db import transaction
from oioioi.contests.models import Contest, ProblemInstance, Submission, \
        SubmissionReport, FailureReport, UserResultForContest, \
        UserResultForRound, UserResultForProblem
import json
import logging
import traceback
import pprint

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

    # We do this in three separate transaction, because in some database
    # engines (namely MySQL in REPEATABLE READ transaction isolation level)
    # data changed by a transaction is not visible in subsequent selects even
    # in the same transaction.

    # First: UserResultForProblem
    with transaction.commit_on_success():
        result, created = UserResultForProblem.objects.select_for_update() \
                .get_or_create(user=user, problem_instance=problem_instance)
        contest.controller.update_user_result_for_problem(result)

    # Second: UserResultForRound
    with transaction.commit_on_success():
        result, created = UserResultForRound.objects.select_for_update() \
                .get_or_create(user=user, round=round)
        contest.controller.update_user_result_for_round(result)

    # Third: UserResultForContest
    with transaction.commit_on_success():
        result, created = UserResultForContest.objects.select_for_update() \
                .get_or_create(user=user, contest=contest)
        contest.controller.update_user_result_for_contest(result)

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

