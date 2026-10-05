from django import forms
from django.conf import settings
from django.forms import modelformset_factory
from django.utils.translation import gettext_lazy as _

from oioioi.newsfeed.models import NewsLanguageVersion


class NewsLanguageVersionForm(forms.ModelForm):
    class Meta:
        model = NewsLanguageVersion
        fields = [
            "language",
            "title",
            "content",
        ]

    language = forms.ChoiceField(
        label=_("Language"),
        choices=settings.LANGUAGES,
        widget=forms.HiddenInput(),
    )

    title = forms.CharField(
        label=_("Title"),
        max_length=255,
    )

    content = forms.CharField(
        label=_("Content"),
        widget=forms.Textarea(attrs={"rows": 10}),
    )


NewsLanguageVersionFormset = modelformset_factory(
    NewsLanguageVersion,
    form=NewsLanguageVersionForm,
    extra=len(settings.LANGUAGES),
    min_num=1,
    max_num=len(settings.LANGUAGES),
    validate_min=True,
    validate_max=True,
    can_delete=True,
)
