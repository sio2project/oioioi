from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.contests.forms import SimpleContestForm
from oioioi.teachers.models import Teacher
from oioioi.base.utils.user_selection import UserSelectionField



class TeacherContestForm(SimpleContestForm):
    class Meta(SimpleContestForm.Meta):
        fields = ['name', 'id']


class AddTeacherForm(forms.ModelForm):
    class Meta(object):
        model = Teacher
        fields = ['user', 'school']

    user = UserSelectionField(label=_("Username"))

    def __init__(self, *args, **kwargs):
        super(AddTeacherForm, self).__init__(*args, **kwargs)
        self.fields['user'].hints_url = reverse('user_search')

    school = forms.CharField(
        label=_("School"),
        help_text=mark_safe(
            _(
                "Please provide the full name. If the "
                "school is a part of a larger organization of schools, "
                "<br>enter the name of this organization."
            )
        ),
    )

    message = forms.CharField(
        label=_("Message"),
        help_text=_(
            "Optional. If provided, this message will be sent to the managers."
        ),
        required=False,
        widget=forms.Textarea(attrs={'rows': 10}),
    )

    def clean_school(self):
        data = self.cleaned_data['school']
        return ' '.join(data.splitlines())


class AdminTeacherForm(forms.ModelForm):
    class Meta(object):
        model = Teacher
        fields = ['user', 'school', 'is_active']

    user = UserSelectionField(label=_("Username"))

    def __init__(self, *args, **kwargs):
        super(AdminTeacherForm, self).__init__(*args, **kwargs)
        self.fields['user'].hints_url = reverse('user_search')
        instance_user = None
        if 'instance' in kwargs:
            instance = kwargs['instance']
            if hasattr(instance, 'user'):
                instance_user = instance.user
        if instance_user is not None:
            self.fields['user'].disabled = True
            self.initial['user'] = instance_user

    school = forms.CharField(
        label=_("School"),
        help_text=mark_safe(
            _(
                "Please provide the full name. If the "
                "school is a part of a larger organization of schools, "
                "<br>enter the name of this organization."
            )
        ),
    )

    def clean_school(self):
        data = self.cleaned_data['school']
        return ' '.join(data.splitlines())
