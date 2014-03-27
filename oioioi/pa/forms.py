from django import forms
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from oioioi.pa.models import PARegistration


class PARegistrationForm(forms.ModelForm):
    class Meta(object):
        model = PARegistration
        exclude = ['participant']

    def __init__(self, *args, **kwargs):
        super(PARegistrationForm, self).__init__(*args, **kwargs)

        self.fields['job'].widget.attrs['class'] = 'input-xlarge'

    def clean_terms_accepted(self):
        if not self.cleaned_data['terms_accepted']:
            raise ValidationError(_("Terms not accepted"))
        return True
