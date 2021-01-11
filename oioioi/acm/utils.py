import six

from oioioi.acm.score import BinaryScore
from oioioi.contests.utils import aggregate_statuses


def acm_test_scorer(test, result):
    status = result['result_code']
    return None, None, status


def acm_group_scorer(test_results):
    status = aggregate_statuses(
        [result['status'] for result in six.itervalues(test_results)]
    )
    return None, None, status


def acm_score_aggregator(group_results):
    if not group_results:
        return None, None, 'OK'
    status = aggregate_statuses(
        [result['status'] for result in six.itervalues(group_results)]
    )
    return BinaryScore(status == 'OK'), BinaryScore(True), status
