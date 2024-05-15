from django import forms
from django.utils.translation import gettext_lazy as _


class ExportSubmissionsForm(forms.Form):
    round = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label=_("All rounds"),
        label=_("Choose round"),
    )
    only_final = forms.BooleanField(
        label=_("Only submissions used for final scoring"), required=False, initial=True
    )

    def __init__(self, request, *args, **kwargs):
        super(ExportSubmissionsForm, self).__init__(*args, **kwargs)
        self.fields['round'].queryset = request.contest.round_set
