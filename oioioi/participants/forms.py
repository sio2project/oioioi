import bleach
from django import forms
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from oioioi.contests.models import Round
from oioioi.participants.models import (
    OpenRegistration,
    Participant,
    Region,
    TermsAcceptedPhrase,
)


class ParticipantForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = Participant

    def clean_user(self):
        if Participant.objects.filter(
            contest=self.request_contest, user=self.cleaned_data['user']
        ).exists() and (
            self.instance is None or self.instance.user_id == None or self.instance.user != self.cleaned_data['user']
        ):
            raise ValidationError(
                _("%s is already a participant of this contest.")
                % self.cleaned_data['user'].username
            )
        return self.cleaned_data['user']


class RegionForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = Region

    def clean_short_name(self):
        if Region.objects.filter(
            contest=self.request_contest, short_name=self.cleaned_data['short_name']
        ).exists() and (
            self.instance is None
            or self.instance.short_name != self.cleaned_data['short_name']
        ):
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
    extra_time = forms.IntegerField(min_value=1, label=_("Extra time (in minutes)"))

    def __init__(self, request_contest, *args, **kwargs):
        super(ExtendRoundForm, self).__init__(*args, **kwargs)
        self.fields['round'] = forms.ModelChoiceField(
            queryset=Round.objects.filter(contest=request_contest)
        )


class TermsAcceptedPhraseForm(forms.ModelForm):
    allowed_tags = [
        'a',
        'article',
        'b',
        'blockquote',
        'br',
        'center',
        'code',
        'em',
        'font',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'i',
        'p',
        'strong',
        'u',
    ]

    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        'font': ['color', 'size'],
        'table': ['align'],
    }

    def tag_as_str(self, tag):
        if tag in self.allowed_attributes:
            return '{} ({})'.format(
                tag, ', '.join(sorted(self.allowed_attributes[tag]))
            )
        else:
            return tag

    class Meta(object):
        model = TermsAcceptedPhrase
        fields = ['text']
        verbose_name = 'fsaf'

    def __init__(self, *args, **kwargs):
        super(TermsAcceptedPhraseForm, self).__init__(*args, **kwargs)

        if 'text' in self.fields:
            self.fields['text'].widget.attrs['class'] = 'monospace'
            self.fields['text'].help_text = _(
                "You can use the following tags and attributes: {}."
            ).format(
                ', '.join(self.tag_as_str(tag) for tag in sorted(self.allowed_tags))
            )

    def clean_content(self):
        return bleach.clean(
            self.cleaned_data['text'],
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True,
        )
