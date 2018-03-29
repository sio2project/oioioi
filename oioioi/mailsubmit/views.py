from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.base.utils.pdf import generate_pdf
from oioioi.contests.utils import (can_enter_contest, contest_exists,
                                   has_any_visible_problem_instance,
                                   is_contest_admin)
from oioioi.default_settings import MAILSUBMIT_CONFIRMATION_HASH_LENGTH
from oioioi.mailsubmit.forms import (AcceptMailSubmissionForm,
                                     MailSubmissionForm)
from oioioi.mailsubmit.models import MailSubmission
from oioioi.mailsubmit.utils import (accept_mail_submission,
                                     has_any_mailsubmittable_problem,
                                     is_mailsubmit_allowed,
                                     mail_submission_hashes)


@menu_registry.register_decorator(_("Postal submission"), lambda request:
        reverse('mailsubmit', kwargs={'contest_id': request.contest.id}),
    order=300)
@enforce_condition(contest_exists & can_enter_contest & is_mailsubmit_allowed
    & has_any_visible_problem_instance & has_any_mailsubmittable_problem)
def mailsubmit_view(request):
    if request.method == 'POST':
        form = MailSubmissionForm(request, request.POST, request.FILES)
        if form.is_valid():
            mailsubmission = MailSubmission(
                user=form.cleaned_data.get('user', request.user),
                problem_instance=form.cleaned_data['problem_instance'],
                date=request.timestamp
            )
            source_file = form.cleaned_data['file']
            if source_file is None:
                lang_exts = getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})
                extension = lang_exts[form.cleaned_data['prog_lang']][0]
                source_file = ContentFile(form.cleaned_data['code'],
                                   '__pasted_code.' + extension)

            mailsubmission.source_file.save(source_file.name, source_file)
            mailsubmission.save()
            return _generate_pdfdoc(request, mailsubmission)
    else:
        form = MailSubmissionForm(request)
    return TemplateResponse(request, 'mailsubmit/submit.html', {'form': form})


@enforce_condition(contest_exists & is_contest_admin)
def accept_mailsubmission_view(request, mailsubmission_id='',
                               mailsubmission_hash=''):
    if request.method == 'POST':
        form = AcceptMailSubmissionForm(request, request.POST)
        if form.is_valid():
            mailsubmission = form.cleaned_data['mailsubmission']
            if mailsubmission.submission is not None:
                messages.info(request, _("Postal submission was already "
                                         "accepted"))
            else:
                accept_mail_submission(request, mailsubmission)
                messages.success(request, _("Postal submission accepted"))
            return redirect('accept_mailsubmission_default',
                            contest_id=request.contest.id)
    else:
        form = AcceptMailSubmissionForm(request, initial={
                'mailsubmission_id': mailsubmission_id,
                'submission_hash': mailsubmission_hash,
        })
    return TemplateResponse(request, 'mailsubmit/accept.html', {
            'form': form,
            'HASH_LENGTH': MAILSUBMIT_CONFIRMATION_HASH_LENGTH
    })


def _generate_pdfdoc(request, mailsubmission):
    source_hash, submission_hash = mail_submission_hashes(mailsubmission)

    accept_link = request.build_absolute_uri(reverse('accept_mailsubmission',
            kwargs={
                'contest_id': request.contest.id,
                'mailsubmission_id': mailsubmission.id,
                'mailsubmission_hash': submission_hash,
            }))

    doc = render_to_string('mailsubmit/submissiondoc.tex',
            context_instance=RequestContext(request, {
                'config': request.contest.mail_submission_config,
                'submission': mailsubmission,
                'contest': request.contest,
                'source_hash': source_hash,
                'submission_hash': submission_hash,
                'qrcode_content': accept_link
            }))

    filename = u'%s-%s-%s.pdf' % (_("confirmation"),
            mailsubmission.problem_instance.short_name,
            mailsubmission.id)

    # The QR code generator needs the permission to run shell commands,
    # that's why we have --shell-escape here.
    # See also: http://www.texdev.net/2009/10/06/what-does-write18-mean/
    return generate_pdf(doc, filename, extra_args=['--shell-escape'])
