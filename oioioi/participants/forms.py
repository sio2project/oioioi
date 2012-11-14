from django import forms
from django.forms import ValidationError
from oioioi.participants.models import Participant

class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant

    def clean_user(self):
        if self.request_contest and Participant.objects.filter(
                contest=self.request_contest, user=self.cleaned_data['user']) \
                .exists():
            raise ValidationError(
                    _("%s is already a participant of this contest.")
                    % self.cleaned_data['user'].username)
        return self.cleaned_data['user']

