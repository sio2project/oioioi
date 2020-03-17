from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.forms import SimpleContestForm
from oioioi.teachers.models import Teacher


class TeacherContestForm(SimpleContestForm):
    class Meta(SimpleContestForm.Meta):
        fields = ['name', 'id']


class AddTeacherForm(forms.ModelForm):
    class Meta(object):
        model = Teacher
        fields = ['school']

    school = forms.CharField(
            label=_("School"),
            help_text=mark_safe(_("Please provide the full name. If the "
                "school is a part of a larger organization of schools, "
                "<br>enter the name of this organization.")))

    message = forms.CharField(
            label=_("Message"),
            help_text=_("Optional. If provided, this message will be sent "
                "to the managers."),
            required=False,
            widget=forms.Textarea(attrs={'rows': 10}))

    def clean_school(self):
        data = self.cleaned_data['school']
        return ' '.join(data.splitlines())
