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

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(readonly=True)

    def clean_username(self):
        instance = getattr(self, 'instance', None)
        if instance:
            return instance.username
        else:
            return self.cleaned_data['username']

# http://stackoverflow.com/questions/3657709/how-to-force-save-an-empty-unchanged-django-admin-inline
class AlwaysChangedModelForm(forms.ModelForm):
    def has_changed(self):
        """By always returning True even unchanged inlines will get saved."""
        return True
