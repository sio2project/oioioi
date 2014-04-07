import string
import random
from django.utils.functional import lazy
from oioioi.contests.utils import can_enter_contest
from django.conf import settings
from django.template.loader import render_to_string

from oioioi.notifications.models import NotificationsSession
from django.contrib.sessions.models import Session


def generate_token():
    new_token = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for _ in range(32))
    # It is very improbable, but it could happen that the generated token
    # is already present in the dictionary. Let's generate new one.
    if NotificationsSession.objects.filter(uid=new_token).exists():
        return generate_token()
    return new_token


def get_notifications_session(session):
    notification_session = NotificationsSession.objects.filter(
        session=session.session_key)
    if not notification_session.exists():
        notification_session = NotificationsSession()
        notification_session.uid = generate_token()
        notification_session.session = \
            Session.objects.get(pk=session.session_key)
        notification_session.save()
    else:
        notification_session = notification_session[0]
    return notification_session


def notification_processor(request):
    if not getattr(request, 'contest', None) or \
        not request.user.is_authenticated() or \
            not can_enter_contest(request):
        return {}
    notifications_session_id = get_notifications_session(request.session).uid

    def generator():
        return render_to_string('notifications/notifications.html',
                                dict(notif_server_url=
                                     settings.NOTIFICATIONS_SERVER_URL,
                                     notifications_session_id=
                                     notifications_session_id))
    return {'extra_navbar_right_notifications': lazy(generator, unicode)()}
