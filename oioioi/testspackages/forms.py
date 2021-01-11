from django import forms
from django.utils.translation import ugettext_lazy as _


class TestsPackageInlineFormSet(forms.models.BaseInlineFormSet):
    @property
    def empty_form(self):
        form = super(TestsPackageInlineFormSet, self).empty_form
        form.initial = {
            'name': '%s_tests' % self.instance.short_name,
            'description': _("Tests for task %s") % self.instance.name,
            'tests': form.fields['tests'].queryset,
        }
        return form
