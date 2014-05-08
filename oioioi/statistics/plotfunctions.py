# -*- coding: utf-8 -*-
from itertools import groupby
from operator import itemgetter
from collections import defaultdict

from django.utils.translation import ugettext as _
from django.db.models import Count

from oioioi.contests.models import Submission, \
        UserResultForProblem, UserResultForContest
from oioioi.contests.scores import IntegerScore
from oioioi.programs.models import ProgramSubmission


def int_score(score):
    return score.value if isinstance(score, IntegerScore) else 0


def histogram(values, num_buckets=10, max_result=None):
    """Calculates the histogram of the provided values (integers).
       Assumes that minimal value is 0.

       :param values: List of integers to compute the histogram.
       :param num_buckets: Number of histogram buckets.
       :returns: A pair of lists (boundaries, counts); boundaries contain
           lower bounds of bucket limits; counts contain the numbers of
           elements going in particular buckets.
    """
    assert num_buckets > 0, "Non positive number of buckets for histogram"

    if max_result is None and values:
        max_result = max(values)

    if max_result:
        if max_result < num_buckets:
            num_buckets = max_result  # divide by zero protection

        bucket = max_result / num_buckets  # bucket cannot be 0
        if (max_result % num_buckets) != 0:
            num_buckets += 1

        counts = [0] * (num_buckets+1)
    else:
        bucket = 1
        counts = [0]

    for key, group in groupby(values, key=(lambda x: x / bucket)):
        counts[key] += len(list(group))

    return [list(tup) for tup in
            zip(*[[i*bucket, value] for i, value in enumerate(counts)])]


def results_histogram_for_queryset(qs, max_score=None):
    scores = [int_score(r.score) for r in qs]

    # Only IntegerScore can be used with the histogram.
    if isinstance(max_score, IntegerScore):
        max_score = max_score.value
    else:
        max_score = None

    keys_left, data = histogram(scores, max_result=max_score)

    keys = ['[%d;%d)' % p for p in zip(keys_left[:-1], keys_left[1:])]
    keys.append('[%d;∞)' % keys_left[-1])

    return {
        'plot_name': _("Results histogram"),
        'data': [data],
        'keys': keys,
        'titles': {'yAxis': _("# of results")},
        'y_min': 0,
        'series': [_("results")]
    }


def points_histogram_contest(contest):
    results = UserResultForContest.objects.filter(contest=contest)
    return results_histogram_for_queryset(results)


def points_histogram_problem(problem):
    results = UserResultForProblem.objects.filter(problem_instance=problem)

    # Check if user has any submissions for the specified problem
    if results and results[0].submission_report is not None:
        max_score = results[0].submission_report \
                .score_report.max_score
    else:
        max_score = None

    return results_histogram_for_queryset(results, max_score=max_score)


def submissions_by_problem_histogram_for_queryset(qs):
    agg = qs.values('problem_instance', 'problem_instance__short_name',
                    'status').annotate(count=Count('problem_instance'))
    agg = sorted(agg, key=itemgetter('status'))
    statuses = list(set(a['status'] for a in agg))
    pis = list(set((a['problem_instance'], a['problem_instance__short_name'])
                    for a in agg))
    d = defaultdict(int)
    for v in agg:
        d[(v['status'], v['problem_instance'])] = v['count']
    data = [[d[s, pi_id] for pi_id, _name in pis] for s in statuses]

    return {
        'plot_name': _("Submissions histogram"),
        'data': data,
        'keys': [pi[1] for pi in pis],
        'titles': {'yAxis': _("# of submissions")},
        'y_min': 0,
        'series': statuses
    }


def submissions_histogram_contest(contest):
    subs = Submission.objects.filter(kind='NORMAL') \
            .filter(problem_instance__contest=contest) \
            .prefetch_related('problem_instance')
    return submissions_by_problem_histogram_for_queryset(subs)


def points_to_source_length_problem(problem):
    submissions = ProgramSubmission.objects.filter(
            problem_instance=problem,
            submissionreport__userresultforproblem__isnull=False)

    data = sorted([[s.source_length, int_score(s.score)] for s in submissions])

    return {
        'plot_name': _("Points vs source length scatter"),
        'data': [data],
        'x_min': 0,
        'y_min': 0,
        'titles': {
            'xAxis': _("Source length (bytes)"),
            'yAxis': _("Points"),
        },
        'series': [problem.short_name],
        'series_extra_options': [{'color': 'rgba(47, 126, 216, 0.5)'}],
    }
