# -*- coding: utf-8 -*-
from itertools import groupby
from operator import itemgetter
from collections import defaultdict

from django.utils.translation import ugettext as _
from django.db.models import Count

from oioioi.contests.models import Submission, ProblemInstance, \
                                   UserResultForProblem, UserResultForContest
from oioioi.contests.scores import IntegerScore
from oioioi.programs.models import ProgramSubmission


def int_score(score):
    return score.value if isinstance(score, IntegerScore) else 0


def histogram(values, num_buckets=10):
    """Calculates the histogram of the provided values (integers).
       Assumes that minimal value is 0.

       :param values: List of integers to compute the histogram.
       :param num_buckets: Number of histogram buckets.
       :returns: A pair of lists (boundaries, counts); boundaries contain
           lower bounds of bucket limits; counts contain the numbers of
           elements going in particular buckets.
    """
    if values:
        max_result = max(values)
    else:
        max_result = 0

    if max_result:
        if max_result < num_buckets:
            num_buckets = max_result # divide by zero protection

        bucket = max_result / num_buckets # bucket cannot be 0
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


def results_histogram_for_queryset(qs):
    scores = [int_score(r.score) for r in qs]

    keys_left, data = histogram(scores)

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


def points_histogram_contest(contest_name):
    results = UserResultForContest.objects.filter(contest_id=contest_name)
    return results_histogram_for_queryset(results)


def points_histogram_problem(problem_name):
    pis = list(ProblemInstance.objects.filter(short_name=problem_name))
    results = UserResultForProblem.objects.filter(problem_instance__in=pis)
    return results_histogram_for_queryset(results)


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


def submissions_histogram_contest(contest_name):
    subs = Submission.objects.filter(kind='NORMAL') \
            .filter(problem_instance__contest=contest_name) \
            .prefetch_related('problem_instance')
    return submissions_by_problem_histogram_for_queryset(subs)


def points_to_source_length_problem(problem_name):
    submissions = ProgramSubmission.objects.filter(
            problem_instance__short_name=problem_name,
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
        'series': [problem_name],
        'series_extra_options': [{'color': 'rgba(47, 126, 216, 0.5)'}],
    }
