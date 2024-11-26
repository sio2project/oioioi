from django import forms
from django.conf import settings
from django.forms import modelformset_factory

from oioioi.welcomepage.models import WelcomePageMessage


class WelcomePageMessageForm(forms.ModelForm):
    class Meta(object):
        model = WelcomePageMessage
        fields = ['content', 'language']

    language = forms.ChoiceField(
        label="Language",
        choices=settings.LANGUAGES,
        widget=forms.HiddenInput(),
    )

    content = forms.CharField(
        label="Content",
        widget=forms.Textarea(attrs={
            'rows': 10,
            'style': 'white-space: pre;',
            'class': 'monospace',
        }),
    )

WelcomePageMessageFormset = modelformset_factory(
    WelcomePageMessage,
    form=WelcomePageMessageForm,
    extra=len(settings.LANGUAGES),
    min_num=1,
    max_num=len(settings.LANGUAGES),
    validate_min=True,
    validate_max=True,
    can_delete=True,
)
