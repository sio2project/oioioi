from django import forms
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.contestexcl.models import ExclusivenessConfig


class ExclusivenessConfigForm(AlwaysChangedModelForm):
    disable = forms.BooleanField(
        label=_("disable?"),
        help_text=_("Caution! If you disable exclusiveness, it can only be re-enabled by a superadmin!"),
        required=False,
    )

    class Meta:
        fields = "__all__"
        model = ExclusivenessConfig

    def clean(self):
        super(ExclusivenessConfigForm, self).clean()
        if self.cleaned_data["disable"] and not self.instance.enabled:
            raise ValidationError(_("This exclusiveness config is already disabled!"))

    def save(self, commit=True):
        instance = super(ExclusivenessConfigForm, self).save(commit=False)
        if self.cleaned_data["disable"]:
            instance.enabled = False
        if commit:
            instance.save()
        return instance
