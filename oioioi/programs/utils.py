from oioioi.contests.scores import ScoreValue, IntegerScore
from oioioi.contests.utils import aggregate_statuses

# TODO: unittests for all functions

def sum_score_aggregator(group_results):
    if not group_results:
        return None, 'OK'

    scores = [ScoreValue.deserialize(result['score'])
              for result in group_results.itervalues()]
    score = sum(scores[1:], scores[0])
    status = aggregate_statuses([result['status']
        for result in group_results.itervalues()])
    return score, status

def sum_group_scorer(test_results):
    """Adds results of all tests inside a test group."""

    if not test_results:
        return None, 'OK'

    scores = [ScoreValue.deserialize(result['score'])
              for result in test_results.itervalues()]
    score = sum(scores[1:], scores[0])
    status = aggregate_statuses([result['status']
        for result in test_results.itervalues()])
    return score, status

def min_group_scorer(test_results):
    """Gets minimal result of all tests inside a test group."""

    scores = [ScoreValue.deserialize(result['score'])
              for result in test_results.itervalues()]
    score = min(scores)
    status = aggregate_statuses([result['status']
        for result in test_results.itervalues()])
    return score, status

def discrete_test_scorer(test, result):
    status = result['result_code']
    score = (status == 'OK') and test['max_score'] or 0
    return IntegerScore(score), status
