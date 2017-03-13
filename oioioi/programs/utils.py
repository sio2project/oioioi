from math import ceil
from operator import itemgetter

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from oioioi.contests.scores import ScoreValue, IntegerScore
from oioioi.contests.models import Submission
from oioioi.contests.utils import aggregate_statuses
from oioioi.programs.models import ProgramSubmission, LibraryProblemData, \
        ReportActionsConfig

def sum_score_aggregator(group_results):
    if not group_results:
        return None, None, 'OK'

    scores = [ScoreValue.deserialize(result['score'])
              for result in group_results.itervalues()]
    max_scores = [ScoreValue.deserialize(result['max_score'])
              for result in group_results.itervalues()]

    # the sum below needs a start value of an appropriate type,
    # the default zero is not suitable
    score = sum(scores[1:], scores[0])
    max_score = sum(max_scores[1:], max_scores[0])
    status = aggregate_statuses([result['status']
        for result in group_results.itervalues()])

    return score, max_score, status


def sum_group_scorer(test_results):
    """Adds results of all tests inside a test group."""

    if not test_results:
        return None, None, 'OK'

    scores = [ScoreValue.deserialize(result['score'])
              for result in test_results.itervalues()]
    max_scores = [ScoreValue.deserialize(result['max_score'])
              for result in test_results.itervalues()]

    score = sum(scores[1:], scores[0])
    max_score = sum(max_scores[1:], max_scores[0])
    status = aggregate_statuses([result['status']
        for result in test_results.itervalues()])

    return score, max_score, status


class UnequalMaxScores(ValueError):
    pass


def min_group_scorer(test_results):
    """Gets minimal result of all tests inside a test group."""

    scores = [ScoreValue.deserialize(result['score'])
              for result in test_results.itervalues()]
    max_scores = [ScoreValue.deserialize(result['max_score'])
              for result in test_results.itervalues()]

    score = min(scores)
    max_score = min(max_scores)
    if max_score != max(max_scores):
        raise UnequalMaxScores("Tests in one group cannot "
                "have different max scores.")

    sorted_results = sorted(test_results.values(), key=itemgetter('order'))
    status = aggregate_statuses([result['status']
        for result in sorted_results])

    return score, max_score, status


def discrete_test_scorer(test, result):
    status = result['result_code']
    max_score = test['max_score']
    score = max_score if status == 'OK' else 0
    return IntegerScore(score), IntegerScore(max_score), status


def threshold_linear_test_scorer(test, result):
    """Full score if took less than half of limit and then decreasing to 1"""
    limit = test.get('exec_time_limit', 0)
    used = result.get('time_used', 0)
    status = result['result_code']
    percentage = result.get('result_percentage', 100)
    max_score = int(ceil(percentage * test['max_score'] / 100.))
    test_max_score = IntegerScore(test['max_score'])

    if status != 'OK':
        return IntegerScore(0), test_max_score, status
    if not limit:
        return IntegerScore(max_score), test_max_score, status

    if used > limit:
        score = 0
        status = 'TLE'
    elif max_score == 0:
        score = 0
    elif used <= limit / 2.:
        score = max_score
    else:
        score = 1 + int((max_score - 1) * ((limit - used) / (limit / 2.)))

    return IntegerScore(score), test_max_score, status


def decode_str(str):
    try:
        str = str.decode('utf-8')
        decode_error = False
    except UnicodeDecodeError:
        str = str.decode('utf-8', 'replace')
        decode_error = True

    return (str, decode_error)


def get_submission_source_file_or_error(request, submission_id):
    """Returns the submission source and filename

       If it does not exist or the user has no rights to see it, then error is
       raised.
    """
    submission = get_object_or_404(ProgramSubmission, id=submission_id)
    pi = submission.problem_instance
    if pi.contest and (not request.contest or
                       request.contest.id != pi.contest.id):
        raise PermissionDenied

    if not pi.controller.can_see_source(request, submission):
        raise PermissionDenied
    return submission.source_file


def has_report_actions_config(problem):
    try:
        return bool(problem.report_actions_config)
    except ReportActionsConfig.DoesNotExist:
        return False

def is_problem_with_library(problem):
    if isinstance(problem, (int, basestring)):
        return LibraryProblemData.objects.filter(problem_id=problem).exists()

    try:
        return bool(problem.libraryproblemdata)
    except LibraryProblemData.DoesNotExist:
        return False
