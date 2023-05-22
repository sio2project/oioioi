import os.path
from math import ceil
from operator import itemgetter  # pylint: disable=E0611

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse

from oioioi.base.utils import make_html_link
from oioioi.contests.models import Submission
from oioioi.contests.scores import IntegerScore, ScoreValue
from oioioi.contests.utils import aggregate_statuses
from oioioi.programs.models import (
    LibraryProblemData,
    ModelProgramSubmission,
    ProgramSubmission,
    ReportActionsConfig,
)


def sum_score_aggregator(group_results):
    if not group_results:
        return None, None, 'OK'

    scores = [
        ScoreValue.deserialize(result['score'])
        for result in group_results.values()
    ]
    max_scores = [
        ScoreValue.deserialize(result['max_score'])
        for result in group_results.values()
    ]

    # the sum below needs a start value of an appropriate type,
    # the default zero is not suitable
    score = sum(scores[1:], scores[0])
    max_score = sum(max_scores[1:], max_scores[0])
    status = aggregate_statuses(
        [result['status'] for result in group_results.values()]
    )

    return score, max_score, status


def sum_group_scorer(test_results):
    """Adds results of all tests inside a test group."""

    if not test_results:
        return None, None, 'OK'

    scores = [
        ScoreValue.deserialize(result['score'])
        for result in test_results.values()
    ]
    max_scores = [
        ScoreValue.deserialize(result['max_score'])
        for result in test_results.values()
    ]

    score = sum(scores[1:], scores[0])
    max_score = sum(max_scores[1:], max_scores[0])
    status = aggregate_statuses(
        [result['status'] for result in test_results.values()]
    )

    return score, max_score, status


class UnequalMaxScores(ValueError):
    pass


def min_group_scorer(test_results):
    """Gets minimal result of all tests inside a test group."""

    scores = [
        ScoreValue.deserialize(result['score'])
        for result in test_results.values()
    ]
    max_scores = [
        ScoreValue.deserialize(result['max_score'])
        for result in test_results.values()
    ]

    score = min(scores)
    max_score = min(max_scores)
    if max_score != max(max_scores):
        raise UnequalMaxScores(
            "Tests in one group cannot have different max scores."
        )

    sorted_results = sorted(list(test_results.values()), key=itemgetter('order'))
    status = aggregate_statuses([result['status'] for result in sorted_results])

    return score, max_score, status


def discrete_test_scorer(test, result):
    status = result['result_code']
    percentage = result.get('result_percentage', 100)
    max_score = int(ceil(percentage * test['max_score'] / 100.))
    score = max_score if status == 'OK' else 0
    return IntegerScore(score), IntegerScore(test['max_score']), status


def threshold_linear_test_scorer(test, result):
    """Full score if took less than half of limit and then decreasing to 1"""
    limit = test.get('exec_time_limit', 0)
    used = result.get('time_used', 0)
    status = result['result_code']
    percentage = result.get('result_percentage', 100)
    max_score = int(ceil(percentage * test['max_score'] / 100.0))
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
    elif used <= limit / 2.0:
        score = max_score
    else:
        score = 1 + int((max_score - 1) * ((limit - used) / (limit / 2.0)))

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
    if pi.contest and (not request.contest or request.contest.id != pi.contest_id):
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
    if isinstance(problem, (int, str)):
        return LibraryProblemData.objects.filter(problem_id=problem).exists()

    try:
        return bool(problem.libraryproblemdata)
    except LibraryProblemData.DoesNotExist:
        return False


def is_model_submission(submission):
    return ModelProgramSubmission.objects.filter(pk=submission.id).exists()


def filter_model_submissions(queryset):
    model_ids = ModelProgramSubmission.objects.values_list('id', flat=True)
    return queryset.exclude(pk__in=model_ids)


def form_field_id_for_langs(problem_instance):
    return 'prog_lang_' + str(problem_instance.id)


def get_problem_link_or_name(request, submission):
    pi = submission.problem_instance
    if pi.contest is None:
        href = reverse(
            'problem_site', kwargs={'site_key': pi.problem.problemsite.url_key}
        )
        return make_html_link(href, pi)
    elif pi.contest.controller.can_see_statement(request, pi):
        href = reverse(
            'problem_statement',
            kwargs={'contest_id': pi.contest_id, 'problem_instance': pi.short_name},
        )
        return make_html_link(href, pi)
    else:
        return pi


def get_extension(file_name):
    return os.path.splitext(file_name)[1][1:]


def get_submittable_languages():
    submittable_languages = getattr(settings, "SUBMITTABLE_LANGUAGES")
    for _, lang_config in submittable_languages.items():
        lang_config.setdefault('type', 'main')
    return submittable_languages
