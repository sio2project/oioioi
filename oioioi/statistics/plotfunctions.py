from itertools import groupby
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Submission, ProblemInstance, \
                                   UserResultForProblem, UserResultForContest
from oioioi.contests.scores import IntegerScore

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
        if (max_result % num_buckets) is not 0:
            num_buckets += 1

        counts = [0] * (num_buckets+1)
    else:
        bucket = 1
        counts = [0]

    for key, group in groupby(values, key=(lambda x: x / bucket)):
        counts[key] += len(list(group))

    return zip(*[(i*bucket, value) for i, value in enumerate(counts)])


def points_histogram_contest(contest_name):
    results = UserResultForContest.objects.filter(contest_id=contest_name)

    scores = [r.score.value if isinstance(r.score, IntegerScore)
              else 0 for r in results]

    keys_left, data = histogram(scores)

    keys = []
    prev = 0
    for current in keys_left[1:]:
        keys.append(str(prev) + '-' + str(current - 1))
        prev = current
    keys.append('>=' + str(prev))

    return {
        'plot_name': _("Points histogram"),
        'data': [data],
        'keys': keys,
        'y_axis_title': _("Points"),
        'columns': [_("points")]
    }


def solutions_histogram_contest(contest_name):
    sub = Submission.objects.filter(kind = 'NORMAL') \
        .filter(problem_instance__contest = contest_name)

    pis = ProblemInstance.objects.filter(contest_id=contest_name)

    counts = {i.short_name: set() for i in pis}

    for i in sub:
        counts[i.problem_instance.short_name].add(i.user)

    if pis:
        (keys, data) = zip(*[(i.short_name,
                             len(counts[i.short_name])) for i in pis])
    else:
        keys = []
        data = []

    return {
        'plot_name': _("Solutions histogram"),
        'data': [data],
        'keys': keys,
        'y_axis_title': _("Solutions"),
        'columns': [_("solutions")]
    }


def submissions_histogram_contest(contest_name):
    counts = {}

    sub = Submission.objects.filter(kind='NORMAL') \
        .filter(problem_instance__contest=contest_name)
    pis = ProblemInstance.objects.filter(contest_id=contest_name)

    counts = {i.short_name: 0 for i in pis}

    for i in sub:
        counts[i.problem_instance.short_name] += 1

    if counts:
        (keys, data) = zip(*[(key.short_name, counts[key.short_name])
                             for key in pis])
    else:
        keys = []
        data = []

    return {
        'plot_name': _("Submissions histogram"),
        'data': [data],
        'keys': keys,
        'y_axis_title': _("Submissions"),
        'columns': [_("submissions")]
    }

def points_histogram_problem(problem_name):
    pis = list(ProblemInstance.objects.filter(short_name=problem_name))
    results = UserResultForProblem.objects.filter(problem_instance__in=pis)

    scores = [r.score.value if isinstance(r.score, IntegerScore)
                    else 0 for r in results]

    keys_left, data = histogram(scores)

    keys = []
    prev = 0
    for current in keys_left[1:]:
        keys.append(str(prev) + '-' + str(current - 1))
        prev = current
    keys.append('>=' + str(prev))

    return {
        'plot_name': _("Points histogram"),
        'data': [data],
        'keys': keys,
        'y_axis_title': _("Points"),
        'columns': [_("points")]
    }
