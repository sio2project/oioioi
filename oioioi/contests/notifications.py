from datetime import datetime  # pylint: disable=E0611
import six

from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.utils.timezone import utc

from oioioi.base.notification import NotificationHandler


def notification_function_submission_judged(arguments):
    assert hasattr(arguments, 'user') and \
           hasattr(arguments, 'submission')
    pi = arguments.submission.problem_instance
    request = RequestFactory().get('/', data={'name': u'test'})
    request.user = arguments.user
    request.contest = pi.contest
    request.timestamp = datetime.now().replace(tzinfo=utc)

    # Check if the final report is visible to the user
    if not pi.contest.controller.can_see_submission_score(request,
            arguments.submission):
        return

    url = reverse('submission',
        kwargs={'contest_id': pi.contest.pk,
        'submission_id': arguments.submission.pk})

    message = pi.contest.controller \
            .get_notification_message_submission_judged(arguments.submission)

    message_arguments = {'short_name': pi.short_name,
                         'contest_name': pi.contest.name,
                         'task_name': six.text_type(pi),
                         'score': six.text_type(arguments.submission.score),
                         'address': url}
    NotificationHandler.send_notification(arguments.user,
        'submission_judged', message, message_arguments)

NotificationHandler.register_notification('submission_judged',
        notification_function_submission_judged)
