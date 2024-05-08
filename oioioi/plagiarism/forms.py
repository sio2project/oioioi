from django import forms
from django.utils.translation import gettext_lazy as _

from oioioi.plagiarism.utils import MOSS_SUPPORTED_LANGUAGES
from oioioi.programs.utils import get_submittable_languages

LANGUAGES = get_submittable_languages()
LANGUAGES = {
    lang: d for lang, d in LANGUAGES.items() if lang in MOSS_SUPPORTED_LANGUAGES
}


class MossSubmitForm(forms.Form):
    problem_instance = forms.ModelChoiceField(
        queryset=None,
        label=_("Choose problem"),
        required=True,
    )
    language = forms.ChoiceField(
        choices=[(lang, d['display_name']) for lang, d in LANGUAGES.items()],
        label=_("Programming language"),
        required=True,
    )
    only_final = forms.BooleanField(
        label=_("Only submissions used for final scoring"), required=False, initial=True
    )
    userid = forms.IntegerField(
        label=_("MOSS user ID"),
        required=True,
        min_value=0,
        max_value=2 ** 32,
    )

    def __init__(self, problem_instances, *args, **kwargs):
        super(MossSubmitForm, self).__init__(*args, **kwargs)
        self.fields['problem_instance'].queryset = problem_instances
