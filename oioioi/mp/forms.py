import datetime

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.mp.models import MPRegistration, MP2025Registration
from oioioi.oi.forms import SchoolSelect


class MPRegistrationForm(forms.ModelForm):
    class Meta(object):
        model = MPRegistration
        exclude = ['participant']

    def set_terms_accepted_text(self, terms_accepted_phrase):
        if terms_accepted_phrase is None:
            self.fields['terms_accepted'].label = _(
                "I declare that I have read the contest rules and "
                "the technical arrangements. I fully understand them and "
                "accept them unconditionally."
            )
        else:
            self.fields['terms_accepted'].label = mark_safe(terms_accepted_phrase.text)

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise ValidationError(_("Terms not accepted"))
        return True


class MP2025RegistrationForm(MPRegistrationForm):
    class Media(object):
        js = ('oi/reg.js',)

    class Meta(object):
        model = MP2025Registration
        exclude = ['participant']

    def __init__(self, *args, **kwargs):
        super(MP2025RegistrationForm, self).__init__(*args, **kwargs)

        this_year = datetime.date.today().year
        self.fields['birth_year'].validators.extend(
            [
                MinValueValidator(this_year - 100),
                MaxValueValidator(this_year),
            ]
        )
        self.fields['school'].widget = SchoolSelect()
        self.fields['school'].label += f' ({_("optional")})'
        self.fields['teacher'].label += f' ({_("optional")})'
