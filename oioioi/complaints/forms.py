from django import forms
from django.utils.translation import ugettext_lazy as _

class AddComplaintForm(forms.Form):
    complaint = forms.CharField(label=_("Complaint"),
            widget=forms.Textarea(attrs={'class': 'input-xxlarge', 'rows': 20}))
