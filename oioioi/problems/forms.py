from collections import OrderedDict

from django import forms
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.input_with_generate import TextInputWithGenerate
from oioioi.contests.models import ProblemStatementConfig
from oioioi.problems.models import ProblemSite


class ProblemUploadForm(forms.Form):
    contest_id = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, contest, existing_problem, *args, **kwargs):
        super(ProblemUploadForm, self).__init__(*args, **kwargs)
        self.round_id = None

        if contest and not existing_problem:
            choices = [(r.id, r.name) for r in contest.round_set.all()]
            if len(choices) >= 2:
                fields = self.fields.items()
                fields[0:0] = [('round_id', forms.ChoiceField(choices,
                        label=_("Round")))]
                self.fields = OrderedDict(fields)
            elif len(choices) == 1:
                self.round_id = choices[0][0]

    def clean(self):
        cleaned_data = super(ProblemUploadForm, self).clean()
        if self.round_id:
            cleaned_data['round_id'] = self.round_id
        return cleaned_data


class PackageUploadForm(ProblemUploadForm):
    package_file = forms.FileField(label=_("Package file"))


class ProblemStatementConfigForm(forms.ModelForm):
    class Meta(object):
        fields = '__all__'
        model = ProblemStatementConfig
        widgets = {
            'visible': forms.RadioSelect()
        }


class ProblemSiteForm(forms.ModelForm):
    class Meta(object):
        fields = ['url_key']
        model = ProblemSite
        widgets = {
            'url_key': TextInputWithGenerate()
        }
