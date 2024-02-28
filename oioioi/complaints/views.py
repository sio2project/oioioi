import urllib
from uuid import uuid4

import urllib.parse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, make_request_condition
from oioioi.complaints.forms import AddComplaintForm
from oioioi.complaints.models import ComplaintsConfig
from oioioi.contests.utils import can_enter_contest, contest_exists, is_contest_admin
from oioioi.participants.models import Participant


@make_request_condition
def can_make_complaint(request):
    if not request.user.is_authenticated:
        return False
    if is_contest_admin(request):
        return False
    try:
        cconfig = request.contest.complaints_config
        ret = cconfig.enabled and request.timestamp >= cconfig.start_date
        if cconfig.end_date is not None:
            ret = ret and request.timestamp <= cconfig.end_date
        return ret
    except ComplaintsConfig.DoesNotExist:
        return False


def get_complaints_email(request):
    """This method allows the contest controller to override the complaints email"""
    if hasattr(request.contest.controller, 'get_complaints_email'):
        return request.contest.controller.get_complaints_email(request)
    return settings.COMPLAINTS_EMAIL


def email_template_context(request, message):
    user = request.user
    contest = request.contest

    try:
        participant = Participant.objects.get(user=user, contest=contest)
        participant_status = participant.get_status_display()
        try:
            participant_status += _(" (%(registration)s)") % dict(
                registration=participant.registration_model
            )
        except ObjectDoesNotExist:
            pass
    except Participant.DoesNotExist:
        participant_status = _("NOT A PARTICIPANT")
        participant = None

    return {
        'user': user,
        'contest': contest,
        'message': message.strip(),
        'user_info': '%s (%s)' % (user.get_full_name(), user),
        'participant': participant,
        'participant_status': participant_status,
        'complaints_email': get_complaints_email(request),
        'submissions_link': request.build_absolute_uri(
            reverse('oioioiadmin:contests_submission_changelist')
            + '?'
            + urllib.parse.urlencode(
                {'user__username': request.user.username}
            )
        ),
    }


def notify_complainer(request, body, message_id, ref_id):
    context = email_template_context(request, body)
    subject = render_to_string('complaints/email-subject.txt', context)
    subject = settings.COMPLAINTS_SUBJECT_PREFIX + ' '.join(
        subject.strip().splitlines()
    )
    body = render_to_string('complaints/complainer-email.txt', context)

    message = EmailMessage(
        subject,
        body,
        context['complaints_email'],
        (request.user.email,),
        headers={
            'Errors-To': context['complaints_email'],
            'Reply-To': context['complaints_email'],
            'Message-ID': '<%s@oioioi>' % message_id,
            'References': '<%s@oioioi>' % ref_id,
        },
    )
    message.send()


def notify_jury(request, body, message_id, ref_id):
    context = email_template_context(request, body)
    subject = render_to_string('complaints/email-subject.txt', context)
    subject = settings.COMPLAINTS_SUBJECT_PREFIX + ' '.join(
        subject.strip().splitlines()
    )
    body = render_to_string('complaints/jury-email.txt', context)

    message = EmailMessage(
        subject,
        body,
        settings.SERVER_EMAIL,
        (context['complaints_email'],),
        headers={
            'Reply-To': request.user.email,
            'Message-ID': '<%s@oioioi>' % message_id,
            'References': '<%s@oioioi>' % ref_id,
        },
    )
    message.send()


def complaint_sent(request):
    return TemplateResponse(
        request,
        'complaints/complaint-sent.html',
        {'complaints_email': get_complaints_email(request)},
    )


@menu_registry.register_decorator(
    _("Complaints"),
    lambda request: reverse('add_complaint', kwargs={'contest_id': request.contest.id}),
    order=400,
)
@enforce_condition(contest_exists & can_enter_contest & can_make_complaint)
def add_complaint_view(request):
    if not hasattr(settings, 'COMPLAINTS_EMAIL') or not hasattr(
        settings, 'COMPLAINTS_SUBJECT_PREFIX'
    ):
        raise ImproperlyConfigured(
            'The oioioi.complaints module needs '
            'COMPLAINTS_EMAIL and COMPLAINTS_SUBJECT_PREFIX set in '
            'settings.'
        )
    if request.method == 'POST':
        form = AddComplaintForm(request.POST)
        if form.is_valid():
            complainer_id = str(uuid4()) + '-compl'
            jury_id = str(uuid4()) + '-compl'
            notify_jury(request, form.cleaned_data['complaint'], jury_id, complainer_id)
            notify_complainer(
                request, form.cleaned_data['complaint'], complainer_id, jury_id
            )
            return redirect('complaint_sent', contest_id=request.contest.id)
    else:
        form = AddComplaintForm()
    return TemplateResponse(request, 'complaints/make.html', {'form': form})
