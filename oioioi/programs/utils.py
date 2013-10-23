from oioioi.contests.scores import ScoreValue, IntegerScore
from oioioi.contests.utils import aggregate_statuses


def sum_score_aggregator(group_results):
    if not group_results:
        return None, None, 'OK'

    scores = [ScoreValue.deserialize(result['score'])
              for result in group_results.itervalues()]
    max_scores = [ScoreValue.deserialize(result['max_score'])
              for result in group_results.itervalues()]

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


class UnequalMaxScores(StandardError):
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
    status = aggregate_statuses([result['status']
        for result in test_results.itervalues()])

    return score, max_score, status


def discrete_test_scorer(test, result):
    status = result['result_code']
    max_score = test['max_score']
    score = (status == 'OK') and max_score or 0
    return IntegerScore(score), IntegerScore(max_score), status


def threshold_linear_test_scorer(test, result):
    """Full score if took less than half of limit and then decreasing to 0."""
    limit = test.get('exec_time_limit', 0)
    used = result.get('time_used', 0)
    status = result['result_code']
    percentage = result.get('result_percentage', 100)
    max_score = int(percentage * test['max_score'] / 100)
    test_max_score = IntegerScore(test['max_score'])

    if status != 'OK':
        return IntegerScore(0), test_max_score, status
    elif not limit:
        return IntegerScore(max_score), test_max_score, status

    if used <= limit / 2.:
        score = max_score
    elif used <= limit:
        score = int(max_score * ((limit - used) / (limit / 2.)))
    else:
        score = 0
        status = 'TLE'

    return IntegerScore(score), test_max_score, status


def decode_str(str):
    try:
        str = str.decode('utf-8')
        decode_error = False
    except UnicodeDecodeError:
        str = str.decode('utf-8', 'replace')
        decode_error = True

    return (str, decode_error)


def slice_str(str, length):
    # After slicing UTF-8 can be invalid.
    return str[:length].decode('utf-8', 'ignore').encode('utf-8')
