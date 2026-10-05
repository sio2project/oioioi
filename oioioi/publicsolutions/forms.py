from django import forms
from django.utils.translation import gettext_lazy as _

from oioioi.publicsolutions.utils import problem_instances_with_any_public_solutions


class FilterPublicSolutionsForm(forms.Form):
    category = forms.ChoiceField(choices=[], label=_("Problem"), required=False)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pis = problem_instances_with_any_public_solutions(request).select_related("problem")
        choices = [(pi.id, pi) for pi in pis]

        choices.insert(0, ("", _("All")))

        self.fields["category"].choices = choices
