from django import forms
from django.forms import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.pa.models import PARegistration


class PARegistrationForm(forms.ModelForm):
    eligible_for_prizes = forms.BooleanField(required=False)
    eligible_for_prizes.label = _("I want to be eligible for prizes.")

    class Meta(object):
        model = PARegistration
        exclude = ['participant']
        help_texts = {'address': (
            "Address fields are optional, required only for prizes."
            )}

    def clean(self):
        cleaned_data = super().clean()
        prize_fields_required = cleaned_data.get('eligible_for_prizes')
        prize_fields_error_msg = _("This field is required to be eligible for prizes.")
        prize_fields = ['address', 'postal_code', 'city', 't_shirt_size']

        for field in prize_fields:
            if prize_fields_required and not cleaned_data.get(field):
                self.add_error(field, prize_fields_error_msg)

        return cleaned_data

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
