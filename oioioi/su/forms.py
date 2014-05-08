from django import forms
from django.core.urlresolvers import reverse
from django.contrib.auth import get_backends
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils.user_selection import UserSelectionField


def authentication_backends():
    for backend in get_backends():
        if getattr(backend, 'supports_authentication', True):
            yield ("%s.%s" % (backend.__module__, backend.__class__.__name__),
                   getattr(backend, 'description', backend.__class__.__name__))


class SuForm(forms.Form):
    user = UserSelectionField(label=_("Username"))
    backend = forms.ChoiceField(label=_("Authentication backend"),
        required=False, choices=authentication_backends())

    def __init__(self, *args, **kwargs):
        super(SuForm, self).__init__(*args, **kwargs)
        self.fields['user'].hints_url = reverse('get_suable_users')
