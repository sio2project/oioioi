from django import forms
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Round
from oioioi.participants.models import OpenRegistration, Participant, Region


class ParticipantForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = Participant

    def clean_user(self):
        if Participant.objects.filter(contest=self.request_contest,
            user=self.cleaned_data['user']).exists() \
            and (self.instance is None or
                 self.instance.user != self.cleaned_data['user']):
            raise ValidationError(_("%s is already a participant"
                    " of this contest.") % self.cleaned_data['user'].username)
        return self.cleaned_data['user']


class RegionForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = Region

    def clean_short_name(self):
        if Region.objects.filter(contest=self.request_contest,
            short_name=self.cleaned_data['short_name']).exists() \
            and (self.instance is None or
                 self.instance.short_name != self.cleaned_data['short_name']):
            raise ValidationError(_("Region with this name already exists."))
        return self.cleaned_data['short_name']


class OpenRegistrationForm(forms.ModelForm):
    class Meta(object):
        model = OpenRegistration
        exclude = ['participant']

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise ValidationError(_("Terms not accepted"))
        return True


class ExtendRoundForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    extra_time = forms.IntegerField(min_value=1,
            label=_("Extra time (in minutes)"))

    def __init__(self, request_contest, *args, **kwargs):
        super(ExtendRoundForm, self).__init__(*args, **kwargs)
        self.fields['round'] = forms.ModelChoiceField(Round.objects
                .filter(contest=request_contest))
