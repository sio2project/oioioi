from collections import OrderedDict

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (PasswordResetForm, UserChangeForm,
                                       UserCreationForm)
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from registration.forms import RegistrationForm

from oioioi.base.preferences import PreferencesSaved
from oioioi.base.utils.user import USERNAME_REGEX
from oioioi.base.utils.validators import ValidationError


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

        fields = self.fields.items()
        fields[1:1] = [
            ('first_name', forms.CharField(label=_("First name"))),
            ('last_name', forms.CharField(label=_("Last name")))
        ]
        self.fields = OrderedDict(fields)


class UserForm(forms.ModelForm):
    class Meta(object):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.allow_login_change = kwargs.pop('allow_login_change', False)
        extra = kwargs.pop('extra', {})

        super(UserForm, self).__init__(*args, **kwargs)

        adjust_username_field(self)
        if not self.allow_login_change:
            self.fields['username'].widget.attrs.update(readonly=True)

        self.fields.update(extra)

    def clean_username(self):
        instance = getattr(self, 'instance', None)
        if instance and not self.allow_login_change:
            if self.cleaned_data['username'] != instance.username:
                raise ValidationError(_("You cannot change your username."))
            return instance.username
        else:
            return self.cleaned_data['username']

    def save(self, *args, **kwargs):
        instance = super(UserForm, self).save(*args, **kwargs)
        PreferencesSaved.send(self)
        return instance


class OioioiUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(OioioiUserCreationForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)


class OioioiUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(OioioiUserChangeForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)


class OioioiPasswordResetForm(PasswordResetForm):
    error_messages = {
        'unknown': _("That email address doesn't have an associated local "
                     "user account."),
    }

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        user_model = get_user_model()

        email = self.cleaned_data["email"]
        users = user_model._default_manager.filter(email__iexact=email)

        if not len(users):
            raise forms.ValidationError(self.error_messages['unknown'])
        if not any(user.is_active for user in users):
            raise forms.ValidationError(self.error_messages['unknown'])
        return email


# http://stackoverflow.com/questions/3657709/how-to-force-save-an-empty-unchanged-django-admin-inline
class AlwaysChangedModelForm(forms.ModelForm):
    def has_changed(self):
        """By always returning True even unchanged inlines will get saved."""
        return True
