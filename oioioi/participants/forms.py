from django import forms
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from oioioi.participants.models import Participant
from oioioi.contests.models import Round


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant

    def clean_user(self):
        if Participant.objects.filter(contest=self.request_contest,
            user=self.cleaned_data['user']).exists() \
            and (self.instance is None or
                 self.instance.user != self.cleaned_data['user']):
            raise ValidationError(_("%s is already a participant"
                    " of this contest.") % self.cleaned_data['user'].username)
        return self.cleaned_data['user']


class ExtendRoundForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    extra_time = forms.IntegerField(min_value=1,
            label=_("Extra time (in minutes)"))

    def __init__(self, request_contest, *args, **kwargs):
        super(ExtendRoundForm, self).__init__(*args, **kwargs)
        self.fields['round'] = forms.ModelChoiceField(Round.objects
                .filter(contest=request_contest))
