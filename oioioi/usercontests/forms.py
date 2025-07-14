from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from oioioi.contests.forms import SimpleContestForm


class UserContestForm(SimpleContestForm):
    class Meta(SimpleContestForm.Meta):
        fields = ["name", "id", "default_submissions_limit", "contact_email"]

    def clean(self):
        if not hasattr(settings, "USER_CONTEST_TIMEOUT"):
            return super(UserContestForm, self).clean()

        if "end_date" in self.cleaned_data.keys():
            if self.cleaned_data["end_date"] is None:
                raise forms.ValidationError(_("Please provide round end date."), code="invalid")
            if self.cleaned_data["end_date"] > settings.USER_CONTEST_TIMEOUT:
                raise forms.ValidationError(
                    _("The contest has to end before %(contests_end)s."),
                    params={"contests_end": settings.USER_CONTEST_TIMEOUT.strftime("%Y-%m-%d %H:%M:%S %Z")},
                    code="invalid",
                )

        return super(UserContestForm, self).clean()
