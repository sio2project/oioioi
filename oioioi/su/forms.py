from django import forms
from django.contrib.auth import get_backends
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.user_selection import UserSelectionField


def authentication_backends():
    for backend in get_backends():
        if getattr(backend, 'supports_authentication', True):
            yield (
                "%s.%s" % (backend.__module__, backend.__class__.__name__),
                getattr(backend, 'description', backend.__class__.__name__),
            )


def no_superuser_validator(user):
    if user.is_superuser:
        raise ValidationError(
            _("Switching to a superuser is not allowed for " "security reasons.")
        )


def user_is_active_validator(user):
    if not user.is_active:
        raise ValidationError(_("You can't log in as inactive user."))


class SuForm(forms.Form):
    user = UserSelectionField(
        label=_("Username"),
        validators=[no_superuser_validator, user_is_active_validator],
    )
    backend = forms.ChoiceField(
        label=_("Authentication backend"),
        required=False,
        choices=authentication_backends(),
    )

    def __init__(self, *args, **kwargs):
        super(SuForm, self).__init__(*args, **kwargs)
        self.fields['user'].hints_url = reverse('get_suable_users')
