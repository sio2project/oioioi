from django import forms
from django.utils.translation import gettext_lazy as _


class AddComplaintForm(forms.Form):
    complaint = forms.CharField(label=_("Complaint"), widget=forms.Textarea(attrs={"rows": 20}))
