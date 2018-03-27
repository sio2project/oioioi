from django import forms
from django.utils.translation import ugettext_lazy as _


class EmptyQuizSourceForm(forms.Form):
    name = forms.CharField(label=_("Quiz name"), required=True)
    short_name = forms.CharField(label=_("Short name"), required=True)
