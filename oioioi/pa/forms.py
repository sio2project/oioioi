from django import forms
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from oioioi.pa.models import PARegistration


class PARegistrationForm(forms.ModelForm):
    class Meta(object):
        model = PARegistration
        exclude = ['participant']

    def set_terms_accepted_text(self, terms_accepted_phrase):
        if terms_accepted_phrase is None:
            self.fields['terms_accepted'].label = \
                _("I declare that I have read the contest rules and "
                    "the technical arrangements. I fully understand them and "
                    "accept them unconditionally.")
        else:
            self.fields['terms_accepted'].label = \
                mark_safe(terms_accepted_phrase.text)

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise ValidationError(_("Terms not accepted"))
        return True
