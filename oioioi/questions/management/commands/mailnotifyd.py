import logging
import time

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils import timezone
from django.utils.translation import ugettext as _

from oioioi.questions.models import Message, QuestionSubscription
from oioioi.questions.views import visible_messages

logger = logging.getLogger(__name__)


def generate_notification(msg, user, mail):
    show_original = msg.top_reference \
            and allowed_to_see(msg.top_reference, user)
    link_m_id = msg.top_reference.id if show_original else msg.id
    context = {
        'msg': msg,
        'show_original': show_original,
        'link_m_id': link_m_id,
        'root': settings.PUBLIC_ROOT_URL
    }

    subject = render_to_string(
        'questions/reply_notification_subject.txt',
        context
    )
    subject = ' '.join(subject.strip().splitlines())
    body = render_to_string(
        'questions/reply_notification_body.txt',
        context
    )

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

    subscriptions = QuestionSubscription.objects \
        .filter(contest=instance.contest)

    if instance.kind == 'PUBLIC':
        # There may be users without an e-mail, filter them out
        mails = [
            (sub.user, sub.user.email)
            for sub in subscriptions
            if sub.user.email
        ]

        # if there are any users with e-mails
        for (user, mail) in mails:
            try_sending(instance, user, mail)

    elif instance.kind == 'PRIVATE':
        author = instance.top_reference.author
        subscriptions = subscriptions.filter(user=author)
        if subscriptions and author.email:
            try_sending(instance, author, author.email)
    # if kind == 'QUESTION', then we simply ignore and mark as sent

    instance.mail_sent = True
    instance.save()


def try_sending(msg, user, mail):
    if allowed_to_see(msg, user):
        email = generate_notification(msg, user, mail)
        email.send(fail_silently=True)
    else:
        # For some reason some message from the past is not
        # visible for a user. We omit this, but make sure to
        # mark this in the logs.
        logmsg = ("Omitting message {} to {}, since"
            "they are not allowed to see it").format(msg, user)
        logger.info(logmsg)


def allowed_to_see(msg, user):
    request = fake_request(user, msg.contest)
    return msg in visible_messages(request)


def fake_request(user, contest):
    request = RequestFactory().get('/', data={'name': u'test'})
    request.user = user
    request.contest = contest
    request.timestamp = timezone.now()
    return request


def candidate_messages(timestamp):
    return Message.objects.filter(mail_sent=False).filter(
        Q(pub_date__lte=timestamp) | Q(pub_date=None)
    )


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
