from django import forms
from django.contrib.auth import get_backends
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


def authentication_backends():
    for backend in get_backends():
        if getattr(backend, 'supports_authentication', True):
            yield ("%s.%s" % (backend.__module__, backend.__class__.__name__),
                   getattr(backend, 'description', backend.__class__.__name__))


class SuForm(forms.Form):
    user = forms.CharField(label=_("Username"))
    backend = forms.ChoiceField(label=_("Authentication backend"),
        required=False, choices=authentication_backends())

    def clean_user(self):
        username = self.cleaned_data['user']
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError(_("Invalid username."))
