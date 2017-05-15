from django import forms
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import visible_problem_instances
from oioioi.default_settings import MAILSUBMIT_CONFIRMATION_HASH_LENGTH
from oioioi.mailsubmit.models import MailSubmission
from oioioi.mailsubmit.utils import is_mailsubmit_allowed, \
        mail_submission_hashes


class MailSubmissionForm(forms.Form):
    problem_instance_id = forms.ChoiceField(label=_("Problem"))

    def __init__(self, request, *args, **kwargs):
        self.kind = 'MAILSUBMIT'
        problem_filter = kwargs.pop('problem_filter', None)

        super(MailSubmissionForm, self).__init__(*args, **kwargs)

        self.request = request

        pis = visible_problem_instances(request)
        if problem_filter:
            pis = problem_filter(pis)

        pi_choices = [(pi.id, unicode(pi)) for pi in pis]
        pi_field = self.fields['problem_instance_id']
        pi_field.choices = pi_choices
        pi_field.widget.attrs['class'] = 'input-xlarge'

        # if problem_instance does not exist any from the current
        # contest is chosen. To change in future.
        # ALSO in contests.forms
        contest = request.contest
        assert contest is not None
        problem_instance = ProblemInstance.objects \
                .filter(contest=contest)[0]
        contest.controller.adjust_submission_form(request, self,
                                                  problem_instance)

    def clean(self):
        cleaned_data = super(MailSubmissionForm, self).clean()
        ccontroller = self.request.contest.controller

        if 'problem_instance_id' not in cleaned_data:
            return cleaned_data

        try:
            pi = ProblemInstance.objects.filter(contest=self.request.contest) \
                    .get(id=cleaned_data['problem_instance_id'])
            cleaned_data['problem_instance'] = pi
        except ProblemInstance.DoesNotExist:
            self._errors['problem_instance_id'] = \
                    self.error_class([_("Invalid problem")])
            del cleaned_data['problem_instance_id']
            return cleaned_data

        decision = is_mailsubmit_allowed(self.request) and \
            ccontroller.can_submit(self.request, pi, check_round_times=False)
        if not decision:
            raise ValidationError(getattr(decision, 'exc',
                                              _("Permission denied")))

        if cleaned_data['prog_lang'] and \
                cleaned_data['prog_lang'] not in \
                pi.controller.get_allowed_languages():
            self._errors['prog_lang'] = \
                    self.error_class([_("Disallowed language")])
            del cleaned_data['prog_lang']
            return cleaned_data

        return ccontroller.validate_submission_form(self.request, pi, self,
                                                    cleaned_data)


class AcceptMailSubmissionForm(forms.Form):
    mailsubmission_id = forms.IntegerField(label=_("ID"))
    submission_hash = forms.RegexField(
            label=_("Confirmation code"),
            regex=r'^[0-9a-fA-F]*$',
            min_length=MAILSUBMIT_CONFIRMATION_HASH_LENGTH,
            max_length=MAILSUBMIT_CONFIRMATION_HASH_LENGTH,
            error_messages={'invalid': _("Value must consist of numbers or "
                "letters from A to F")})

    def __init__(self, request, *args, **kwargs):
        super(AcceptMailSubmissionForm, self).__init__(*args, **kwargs)
        self.request = request

    def clean(self):
        cleaned_data = super(AcceptMailSubmissionForm, self).clean()
        if 'mailsubmission_id' not in cleaned_data \
                or 'submission_hash' not in cleaned_data:
            return cleaned_data

        mailsubmission_id = cleaned_data['mailsubmission_id']
        submission_hash = cleaned_data['submission_hash'].lower()

        try:
            mailsubmission = MailSubmission.objects.get(id=mailsubmission_id)
        except MailSubmission.DoesNotExist:
            raise ValidationError(_("Postal submission number %s does not "
                "exist") % (mailsubmission_id,))

        if mailsubmission.problem_instance.contest != self.request.contest:
            raise ValidationError(_("Postal submission number %s is for a "
                "different contest") % (mailsubmission_id,))

        _source_hash, mailsubmission_hash = \
                mail_submission_hashes(mailsubmission)
        if submission_hash != mailsubmission_hash:
            raise ValidationError(_("Invalid confirmation code"))

        cleaned_data['mailsubmission'] = mailsubmission

        return cleaned_data
