from django import forms
from django.utils.translation import ugettext_lazy as _

from oioioi.problems.forms import PackageUploadForm


class ZeusProblemForm(PackageUploadForm):
    zeus_id = forms.ChoiceField(label=_("Zeus ID"))
    zeus_problem_id = forms.IntegerField(required=True, label=_("Zeus Problem ID"))

    def __init__(self, zeus_instances, contest, *args, **kwargs):
        super(ZeusProblemForm, self).__init__(contest, *args, **kwargs)
        zeus_id_field = self.fields['zeus_id']

        if len(zeus_instances) > 1:
            zeus_id_field.choices = [('', '')] + zeus_instances
        else:
            zeus_id_field.choices = zeus_instances
