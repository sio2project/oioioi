from django import forms
from django.conf import settings
from django.forms import ValidationError
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.forms import SubmissionForm
from oioioi.contests.models import ProblemInstance

class OISubmitSubmissionForm(SubmissionForm):

    def __init__(self, request, *args, **kwargs):
        super(OISubmitSubmissionForm, self).__init__(request, *args, **kwargs)
        self.fields['problem_shortname'] = \
            forms.CharField(label=_("problem short name"))
        self.fields['localtime'] = \
            forms.DateTimeField(label=_("local time"), required=False)
        self.fields['siotime'] = \
            forms.DateTimeField(label=_("sio time"), required=False)
        self.fields['magickey'] = \
            forms.CharField(label=_("magic key"))
        del self.fields['problem_instance_id']

    def clean_magickey(self):
        data = self.cleaned_data['magickey']
        if data != settings.OISUBMIT_MAGICKEY:
            raise ValidationError(_("Magickey is not valid."))

        return data

    def clean(self, **kwargs):
        cleaned_data = self.cleaned_data

        try:
            pi = ProblemInstance.objects.filter(contest=self.request.contest) \
                    .get(short_name=self.cleaned_data['problem_shortname'])
            cleaned_data['problem_instance_id'] = pi.id
            del cleaned_data['problem_shortname']
        except ProblemInstance.DoesNotExist:
            self._errors['problem_shortname'] = \
                self.error_class([_("Invalid problem shortname")])
            if 'problem_instance_id' in cleaned_data:
                del cleaned_data['problem_instance_id']
            return cleaned_data

        return super(OISubmitSubmissionForm, self) \
                    .clean(check_submission_limit=False,
                        check_round_times=False)
