from django import forms

from oioioi.usergroups.models import UserGroup


class AddUserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = ['name']


class UserGroupChangeNameForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = ['name']
