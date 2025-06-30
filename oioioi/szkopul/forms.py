import datetime

from django import forms
from django.utils.safestring import mark_safe

from oioioi.oi.forms import OIRegistrationForm
from oioioi.szkopul.models import MAPCourseRegistration


class MAPCourseRegistrationForm(forms.ModelForm):
    class Meta(object):
        model = MAPCourseRegistration
        exclude = ['participant']

    def __init__(self, *args, **kwargs):
        super(MAPCourseRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['not_primaryschool'].label = 'Uczęszczam do szkoły średniej'

    def clean(self):
        super(MAPCourseRegistrationForm, self).clean()
