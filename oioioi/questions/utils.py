from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode


# taken from django.contrib.admin.options.ModelAdmin
def log_addition(request, object):
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_unicode(object),
        action_flag=ADDITION
    )


def send_email_about_new_question(recipient, request, msg_obj):
    context = {'recipient': recipient, 'msg': msg_obj,
               'msg_link': request.build_absolute_uri(
                   reverse('message',
                           kwargs={
                               'contest_id': request.contest.id,
                               'message_id': msg_obj.id
                           })
               )}

    subject = render_to_string('questions/new_msg_mail_subject.txt', context)
    subject = ' '.join(subject.strip().splitlines())
    body = render_to_string('questions/new_msg_mail_body.txt', context)

    email = EmailMessage(subject=subject, body=body, to=[recipient.email])
    email.send(fail_silently=True)
