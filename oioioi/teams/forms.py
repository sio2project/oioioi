from django import forms
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _

from oioioi.teams.models import Team


class TeamForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Team


class CreateTeamForm(forms.Form):
    name = forms.CharField(max_length=50, help_text=_("The public name of the team"))
    login = forms.CharField(
        max_length=50,
        help_text=_("The login should be a short identifier which may be displayed in places where the full name is too long."),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(CreateTeamForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"]
        if Team.objects.filter(contest=self.request.contest, name=name).exists():
            raise ValidationError(_("There already exists a team with that name"))
        return name

    def clean_login(self):
        login = self.cleaned_data.get("login")
        if User.objects.filter(username=login).exists():
            raise ValidationError(_("There already exists a team with that login"))
        return login
