from datetime import datetime  # pylint: disable=E0611

from django.test import RequestFactory
from django.urls import reverse
from django.utils.timezone import utc

from oioioi.base.notification import NotificationHandler


def notification_function_submission_judged(arguments):
    assert hasattr(arguments, 'user') and hasattr(arguments, 'submission')
    pi = arguments.submission.problem_instance
    request = RequestFactory().get('/', data={'name': u'test'})
    request.user = arguments.user
    request.contest = pi.contest
    request.timestamp = datetime.now().replace(tzinfo=utc)

    # Check if the final report is visible to the user
    if pi.contest != None and not pi.contest.controller.can_see_submission_score(
        request, arguments.submission
    ):
        return

    if pi.contest:
        url = reverse(
            'submission',
            kwargs={
                'contest_id': pi.contest.pk,
                'submission_id': arguments.submission.pk,
            },
        )
    elif pi.problem.problemsite:
        url = (
            reverse('problem_site', kwargs={'site_key': pi.problem.problemsite.url_key})
            + '?key=submissions'
        )
    else:
        url = ''

    message = pi.controller.get_notification_message_submission_judged(
        arguments.submission
    )

    message_arguments = {
        'short_name': pi.short_name,
        'task_name': str(pi),
        'score': str(arguments.submission.score),
        'address': url,
        'submission_id': arguments.submission.pk,
    }
    if pi.contest:
        message_arguments['contest_name'] = pi.contest.name
        
    NotificationHandler.send_notification(
        arguments.user, 'submission_judged', message, message_arguments
    )


NotificationHandler.register_notification(
    'submission_judged', notification_function_submission_judged
)
