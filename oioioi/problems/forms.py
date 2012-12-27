from django import forms
from django.utils.translation import ugettext_lazy as _

class ProblemUploadForm(forms.Form):
    contest_id = forms.CharField(widget=forms.HiddenInput, required=False)
    package_file = forms.FileField(label=_("Package file"))

    def __init__(self, contest, *args, **kwargs):
        super(ProblemUploadForm, self).__init__(*args, **kwargs)

        if contest:
            self.fields['submissions_limit'] = \
                forms.IntegerField(required=False)
            self.fields['submissions_limit'].initial = \
                contest.default_submissions_limit
            choices = [(r.id, r.name) for r in contest.round_set.all()]
            if len(choices) == 1:
                self.fields.insert(0, 'round_id', forms.CharField(
                    widget=forms.HiddenInput, initial=choices[0][0]))
            else:
                self.fields.insert(0, 'round_id', forms.ChoiceField(
                    choices, label=_("Round")))


