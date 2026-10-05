from django import forms
from django.utils.translation import gettext_lazy as _


class TestsPackageInlineFormSet(forms.models.BaseInlineFormSet):
    @property
    def empty_form(self):
        form = super().empty_form
        form.initial = {
            "name": f"{self.instance.short_name}_tests",
            "description": _("Tests for task %s") % self.instance.name,
            "tests": form.fields["tests"].queryset,
        }
        return form
