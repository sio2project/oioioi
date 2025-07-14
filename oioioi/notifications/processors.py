import random
import string

from django.conf import settings
from django.contrib.sessions.models import Session
from django.template.loader import render_to_string
from django.utils.functional import lazy

from oioioi.notifications.models import NotificationsSession


def generate_token():
    new_token = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
    # It is very improbable, but it could happen that the generated token
    # is already present in the dictionary. Let's generate new one.
    if NotificationsSession.objects.filter(uid=new_token).exists():
        return generate_token()
    return new_token


def get_notifications_session(session):
    try:
        return NotificationsSession.objects.get(session=session.session_key)
    except NotificationsSession.DoesNotExist:
        notifications_session = NotificationsSession()
        notifications_session.uid = generate_token()
        notifications_session.session = Session.objects.get(pk=session.session_key)
        notifications_session.save()
        return notifications_session


def notification_processor(request):
    if not request.user.is_authenticated:
        return {}

    def generator():
        notifications_session_id = get_notifications_session(request.session).uid
        return render_to_string(
            "notifications/notifications.html",
            dict(
                notif_server_url=settings.NOTIFICATIONS_SERVER_URL,
                notifications_session_id=notifications_session_id,
            ),
        )

    return {"extra_navbar_right_notifications": lazy(generator, str)()}
