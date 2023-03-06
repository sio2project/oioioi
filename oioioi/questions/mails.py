from django.core.mail import EmailMessage
from django.dispatch import Signal, receiver
from django.template.loader import render_to_string
from django.urls import reverse

from oioioi.questions.models import MessageNotifierConfig

new_question_signal = Signal()


@receiver(new_question_signal)
def notify_about_new_question(sender, request, instance, **kwargs):
    conf = MessageNotifierConfig.objects.filter(contest=instance.contest)
    users_to_notify = [x.user for x in conf]
    for u in users_to_notify:
        send_email_about_new_question(u, request, instance)


def send_email_about_new_question(recipient, request, msg_obj):
    context = {
        'recipient': recipient,
        'msg': msg_obj,
        'msg_link': request.build_absolute_uri(
            reverse(
                'message',
                kwargs={'contest_id': request.contest.id, 'message_id': msg_obj.id},
            )
        ),
    }

    subject = render_to_string('questions/new_msg_mail_subject.txt', context)

    subject = ' '.join(subject.strip().splitlines())
    body = render_to_string('questions/new_msg_mail_body.txt', context)

    email = EmailMessage(subject=subject, body=body, to=[recipient.email])
    email.send(fail_silently=True)
