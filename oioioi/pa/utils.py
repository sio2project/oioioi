from oioioi.contests.utils import aggregate_statuses
from oioioi.contests.scores import ScoreValue, IntegerScore
from oioioi.pa.score import PAScore


def pa_test_scorer(test, result):
    status = result['result_code']
    max_score = min(1, test['max_score'])
    score = max_score if status == 'OK' else 0
    return IntegerScore(score), IntegerScore(max_score), status


def pa_score_aggregator(group_results):
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

    return PAScore(score), PAScore(max_score), status
