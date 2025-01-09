# coding: utf-8
import bleach
from collections import OrderedDict

from django.contrib.auth.models import Permission
from captcha.fields import CaptchaField, CaptchaTextInput
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    PasswordResetForm,
    UserChangeForm,
    UserCreationForm,
)
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.forms import BooleanField, ChoiceField
from django.forms import ChoiceField
from django.utils.translation import gettext_lazy as _
from registration.forms import RegistrationForm

from oioioi.base.models import Consents, PreferencesSaved
from oioioi.base.preferences import PreferencesFactory, ensure_preferences_exist_for_user
from oioioi.base.utils.user import UNICODE_CATEGORY_LIST, USERNAME_REGEX
from oioioi.base.utils.validators import UnicodeValidator, ValidationError


def adjust_username_field(form):
    help_text = _("This value may contain only letters, numbers and underscore.")
    form.fields['username'].error_messages['invalid'] = _("Invalid username")
    form.fields['username'].help_text = help_text
    form.fields['username'].validators += [RegexValidator(regex=USERNAME_REGEX)]


def adjust_name_fields(form):
    help_text = _("This value may contain only letters, numbers and punctuation marks.")
    adjust_unicode_field(form, 'first_name', help_text, _("Invalid first name"))
    adjust_unicode_field(form, 'last_name', help_text, _("Invalid last name"))


def adjust_unicode_field(
    form,
    field_name,
    help_text,
    invalid_message,
    unicode_categories=None,
    allow_spaces=True,
):
    if unicode_categories is None:
        unicode_categories = UNICODE_CATEGORY_LIST
    form.fields[field_name].error_messages['invalid'] = invalid_message
    form.fields[field_name].help_text = help_text

    form.fields[field_name].validators += [
        UnicodeValidator(
            unicode_categories=unicode_categories, allow_spaces=allow_spaces
        )
    ]


def get_consent(field_name, user):
    if hasattr(user, 'consents'):
        return getattr(user.consents, field_name)
    else:
        return False


def _maybe_add_field(label, *args, **kwargs):
    if label:
        kwargs.setdefault('label', label)
        PreferencesFactory.add_field(*args, **kwargs)

def adjust_preferences_factory_fields():
    choices_not_translated = [("", "None")] + list(settings.LANGUAGES)
    choices = [(k, _(v)) for k, v in choices_not_translated]

    def handle_preferred_language(user):
        if user is None:
            return "None"
        ensure_preferences_exist_for_user(user)
        return user.userpreferences.language

    PreferencesFactory.add_field(
        "preferred_language",
        ChoiceField,
        lambda name, user: handle_preferred_language(user),
        label=_("Preferred language"),
        choices=choices,
        required=False
    )

    def handle_enable_editor(user):
        if user is None:
            return False
        ensure_preferences_exist_for_user(user)
        return user.userpreferences.enable_editor

    if settings.USE_ACE_EDITOR:
        PreferencesFactory.add_field(
            "enable_editor",
            BooleanField,
            lambda name, user: handle_enable_editor(user),
            label=_("Enable editor"),
            order=0,
            required=False
        )

def handle_new_preference_fields(request, user):
    changed = False
    ensure_preferences_exist_for_user(user)
    if "preferred_language" in request.POST:
        pref_lang = request.POST["preferred_language"]

        if pref_lang in ([k for k, _ in settings.LANGUAGES] + [""]):
            ensure_preferences_exist_for_user(user)

            if pref_lang != "":
                request.COOKIES[settings.LANGUAGE_COOKIE_NAME] = pref_lang
            user.userpreferences.language = pref_lang
            changed = True

    if settings.USE_ACE_EDITOR:
        if "enable_editor" in request.POST:
            user.userpreferences.enable_editor = True
        else:
            user.userpreferences.enable_editor = False
        changed = True

    if changed:
        user.userpreferences.save()

_maybe_add_field(
    settings.REGISTRATION_RULES_CONSENT,
    'terms_accepted',
    forms.BooleanField,
    get_consent,
    required=True,
)

_maybe_add_field(
    settings.REGISTRATION_MARKETING_CONSENT,
    'marketing_consent',
    forms.BooleanField,
    get_consent,
    required=False,
)

_maybe_add_field(
    settings.REGISTRATION_PARTNER_CONSENT,
    'partner_consent',
    forms.BooleanField,
    get_consent,
    required=False,
)

adjust_preferences_factory_fields()

def save_consents(sender, user, **kwargs):
    form = sender
    consents = None
    if hasattr(user, 'consents'):
        consents = user.consents
    else:
        consents = Consents(user=user)

    if 'terms_accepted' in form.cleaned_data:
        consents.terms_accepted = form.cleaned_data['terms_accepted']
    if 'marketing_consent' in form.cleaned_data:
        consents.marketing_consent = form.cleaned_data['marketing_consent']
    if 'partner_consent' in form.cleaned_data:
        consents.partner_consent = form.cleaned_data['partner_consent']

    consents.save()


PreferencesSaved.connect(save_consents)


class CustomCaptchaTextInput(CaptchaTextInput):
    template_name = 'captcha/custom_field.html'


class RegistrationFormWithNames(RegistrationForm):
    class Media(object):
        js = ('js/refresh-simple-captcha.js',)

    def __init__(self, *args, **kwargs):
        extra = kwargs.pop('extra', {})
        super(RegistrationFormWithNames, self).__init__(*args, **kwargs)
        adjust_username_field(self)
        tmp_fields = list(self.fields.items())
        tmp_fields[1:1] = [
            ('first_name', forms.CharField(label=_("First name"))),
            ('last_name', forms.CharField(label=_("Last name"))),
        ]
        self.fields = OrderedDict(tmp_fields)
        self.fields.update(extra)
        self.fields.update(
            {'captcha': CaptchaField(label='', widget=CustomCaptchaTextInput)}
        )
        adjust_name_fields(self)


class UserForm(forms.ModelForm):
    class Meta(object):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.allow_login_change = kwargs.pop('allow_login_change', False)
        extra = kwargs.pop('extra', {})

        super(UserForm, self).__init__(*args, **kwargs)

        adjust_username_field(self)
        adjust_name_fields(self)

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
        PreferencesSaved.send(self, user=instance)
        return instance

class OioioiUserForm(UserForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)

    class Media(object):
        js = ('js/email-change.js',)

    def __init__(self,  *args, **kwargs):

        super(OioioiUserForm, self).__init__(*args, **kwargs)
        self.user = kwargs.pop('instance', None)

    def clean_confirm_password(self):
        confirm_password = self.cleaned_data["confirm_password"]

        if 'email' not in self.cleaned_data:
            return confirm_password

        if self.user.email == self.cleaned_data['email']:
            return confirm_password

        if not self.user.check_password(confirm_password):
            raise forms.ValidationError(_("Password incorrect."), code='password_incorrect', )
        return confirm_password


class OioioiUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(OioioiUserCreationForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)


class OioioiUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super(OioioiUserChangeForm, self).__init__(*args, **kwargs)
        adjust_username_field(self)
        adjust_name_fields(self)
        self.fields['user_permissions'].queryset = Permission.objects.filter(codename='can_modify_tags')


class OioioiPasswordResetForm(PasswordResetForm):
    error_messages = {
        'unknown': _(
            "That email address doesn't have an associated local user account."
        ),
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


class PublicMessageForm(forms.ModelForm):
    allowed_tags = [
        'a',
        'abbr',
        'acronym',
        'article',
        'b',
        'blockquote',
        'br',
        'center',
        'code',
        'em',
        'font',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'hr',
        'i',
        'img',
        'li',
        'ol',
        'p',
        'strong',
        'table',
        'td',
        'th',
        'tr',
        'u',
        'ul',
    ]

    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        'acronym': ['title'],
        'abbr': ['title'],
        'img': ['src', 'width', 'height'],
        'font': ['color', 'size'],
        'table': ['align'],
    }

    def tag_as_str(self, tag):
        if tag in self.allowed_attributes:
            return '{} ({})'.format(
                tag, ', '.join(sorted(self.allowed_attributes[tag]))
            )
        else:
            return tag

    def __init__(self, request, *args, **kwargs):
        super(PublicMessageForm, self).__init__(*args, **kwargs)
        self.fields['content'].widget.attrs['class'] = 'monospace'
        self.contest = request.contest
        self.fields['content'].help_text = _(
            "You can use the following tags and attributes: {}."
        ).format(', '.join(self.tag_as_str(tag) for tag in sorted(self.allowed_tags)))

    def clean_content(self):
        return bleach.clean(
            self.cleaned_data['content'],
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True,
        )

    def save(self, commit = True, *args, **kwargs):
        instance = super(PublicMessageForm, self).save(commit=False, *args, **kwargs)
        instance.contest = self.contest
        if commit:
            instance.save()
        return instance
