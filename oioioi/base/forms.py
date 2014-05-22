import re

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from registration.forms import RegistrationForm

from oioioi.base.utils.validators import ValidationError
from oioioi.base.utils.user import USERNAME_REGEX


def adjust_username_field(form):
    help_text = \
            _("This value may contain only letters, numbers and underscore.")
    form.fields['username'].error_messages['invalid'] = _("Invalid username")
    form.fields['username'].help_text = help_text
    form.fields['username'].validators += \
            [RegexValidator(regex=USERNAME_REGEX)]


class RegistrationFormWithNames(RegistrationForm):
    def __init__(self, *args, **kwargs):
        super(RegistrationFormWithNames, self).__init__(*args, **kwargs)
        adjust_username_field(self)

        self.fields.insert(1, 'first_name',
                forms.CharField(label=_("First name")))
        self.fields.insert(2, 'last_name',
                forms.CharField(label=_("Last name")))


class UserForm(forms.ModelForm):
    class Meta(object):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.allow_login_change = kwargs.pop('allow_login_change', False)
        super(UserForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)
        if not self.allow_login_change:
            self.fields['username'].widget.attrs.update(readonly=True)

    def clean_username(self):
        instance = getattr(self, 'instance', None)
        if instance and not self.allow_login_change:
            if self.cleaned_data['username'] != instance.username:
                raise ValidationError(_("You cannot change your username."))
            return instance.username
        else:
            return self.cleaned_data['username']


class OioioiUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(OioioiUserCreationForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)


class OioioiUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(OioioiUserChangeForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)


# http://stackoverflow.com/questions/3657709/how-to-force-save-an-empty-unchanged-django-admin-inline
class AlwaysChangedModelForm(forms.ModelForm):
    def has_changed(self):
        """By always returning True even unchanged inlines will get saved."""
        return True
