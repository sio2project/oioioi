import logging
import time

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from oioioi.questions.models import Message, QuestionSubscription, notify_private_message
from oioioi.questions.views import visible_messages

logger = logging.getLogger(__name__)


def generate_notification(msg, user, mail):
    show_original = msg.top_reference and allowed_to_see(msg.top_reference, user)
    link_m_id = msg.top_reference.id if show_original else msg.id
    message_url = reverse("message", kwargs={"contest_id": msg.contest.id, "message_id": link_m_id})
    if msg.top_reference_id is not None and msg.top_reference.kind == "PRIVATE":
        message_url = msg.get_absolute_url()
    context = {
        "msg": msg,
        "private_conversation": msg.top_reference_id is not None and msg.top_reference.kind == "PRIVATE",
        "show_original": show_original,
        "message_url": message_url,
        "root": settings.PUBLIC_ROOT_URL,
    }

    subject = render_to_string("questions/reply_notification_subject.txt", context)
    subject = " ".join(subject.strip().splitlines())
    body = render_to_string("questions/reply_notification_body.txt", context)

    return EmailMessage(subject=subject, body=body, to=[mail])


def mailnotify(instance):
    # We should only pass messages with unsent mail here, published in the past
    # We check the visible_messages just to be fail safe.
    assert not instance.mail_sent
    # For some reason instance.pub_date is None if not explicitly set.
    # It would be best to make it not-None by default (and set pub_date
    # to equal creation date) but it is out of scope of this commit
    # hence the first part of the assertion
    assert instance.pub_date is None or instance.pub_date <= timezone.now()

    subscriptions = QuestionSubscription.objects.filter(contest=instance.contest)

    private_recipients = get_private_message_recipients(instance)

    if private_recipients is not None:
        for user in private_recipients:
            if not allowed_to_see(instance, user):
                logmsg = f"Omitting message {instance} to {user}, since they are not allowed to see it"
                logger.info(logmsg)
                continue
            notify_private_message(instance, user)
            if subscriptions.filter(user=user).exists() and user.email:
                try_sending(instance, user, user.email)

    elif instance.kind == "PUBLIC":
        # There may be users without an e-mail, filter them out
        mails = [(sub.user, sub.user.email) for sub in subscriptions if sub.user.email]

        # if there are any users with e-mails
        for user, mail in mails:
            try_sending(instance, user, mail)

    elif instance.kind == "PRIVATE" and instance.top_reference_id is not None:
        author = instance.top_reference.author
        subscriptions = subscriptions.filter(user=author)
        if subscriptions and author.email:
            try_sending(instance, author, author.email)
    # if kind == 'QUESTION', then we simply ignore and mark as sent

    instance.mail_sent = True
    instance.save()


def get_private_message_recipients(instance):
    if instance.kind != "PRIVATE":
        return None

    if instance.top_reference_id is None:
        if instance.recipients.exists():
            return instance.recipients.all()
        return None

    if instance.top_reference.kind != "PRIVATE":
        return None

    recipient = instance.recipients.first()
    if recipient is None:
        return []
    if instance.author_id == recipient.id:
        return [instance.top_reference.author]
    return [recipient]


def try_sending(msg, user, mail):
    if allowed_to_see(msg, user):
        email = generate_notification(msg, user, mail)
        email.send(fail_silently=True)
    else:
        # For some reason some message from the past is not
        # visible for a user. We omit this, but make sure to
        # mark this in the logs.
        logmsg = f"Omitting message {msg} to {user}, since they are not allowed to see it"
        logger.info(logmsg)


def allowed_to_see(msg, user):
    request = fake_request(user, msg.contest)
    return msg in visible_messages(request)


def fake_request(user, contest):
    request = RequestFactory().get("/", data={"name": "test"})
    request.user = user
    request.contest = contest
    request.timestamp = timezone.now()
    return request


def candidate_messages(timestamp):
    return Message.objects.filter(mail_sent=False).filter(Q(pub_date__lte=timestamp) | Q(pub_date=None))


class Command(BaseCommand):
    help = _(
        """
        Periodically scans the whole database for messages with unsent
        notifications.
        We can't do this easily without a daemon since we have to support
        delayed publishing of news.
        """
    )

    def handle(self, *args, **options):
        while True:
            for msg in candidate_messages(timezone.now()):
                mailnotify(msg)
            time.sleep(settings.MAILNOTIFYD_INTERVAL)
