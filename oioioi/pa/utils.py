from oioioi.contests.scores import IntegerScore


def pa_test_scorer(test, result):
    status = result['result_code']
    max_score = min(1, test['max_score'])
    score = max_score if status == 'OK' else 0
    return IntegerScore(score), IntegerScore(max_score), status
