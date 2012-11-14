from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from registration.forms import RegistrationForm

class RegistrationFormWithNames(RegistrationForm):
    def __init__(self, *args, **kwargs):
        super(RegistrationFormWithNames, self).__init__(*args, **kwargs)
        self.fields.insert(1, 'first_name',
                forms.CharField(label=_("First name")))
        self.fields.insert(2, 'last_name',
                forms.CharField(label=_("Last name")))

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

