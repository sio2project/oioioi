from datetime import datetime  # pylint: disable=E0611

from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.utils.timezone import utc
from django.utils.translation import ugettext_noop

from oioioi.base.notification import NotificationHandler


def notification_function_initial_results(arguments):
    assert hasattr(arguments, 'user') and \
           hasattr(arguments, 'submission')
    pi = arguments.submission.problem_instance
    request = RequestFactory().get('/', data={'name': u'test'})
    request.user = arguments.user
    request.contest = pi.contest
    request.timestamp = datetime.now().replace(tzinfo=utc)

    # Check if any initial result is visible for user
    if not pi.controller \
            .can_see_submission_status(request, arguments.submission):
        return

    if pi.contest:
        url = reverse('submission',
            kwargs={'contest_id': pi.contest.pk,
            'submission_id': arguments.submission.pk})
    elif pi.problem.problemsite:
        url = reverse('problem_site', kwargs={
                'site_key': pi.problem.problemsite.url_key}) \
                + '?key=submissions'
    else:
        url = ''

    message = ugettext_noop("Initial result for task %(short_name)s is ready")
    message_arguments = {'short_name': pi.short_name,
        'address': url}

    NotificationHandler.send_notification(arguments.user,
        'initial_results', message, message_arguments)

NotificationHandler.register_notification('initial_results',
        notification_function_initial_results)
