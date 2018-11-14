from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.base.utils import generate_key
from oioioi.contests.models import Contest


class Team(models.Model):
    name = models.CharField(max_length=50, verbose_name=_("team name"))
    login = models.CharField(max_length=50, verbose_name=_("login"))
    user = models.OneToOneField(User, primary_key=True, verbose_name=_("user"))
    contest = models.ForeignKey(Contest)
    join_key = models.CharField(max_length=40)

    def save(self, *args, **kwargs):
        if not hasattr(self, 'user'):
            self.user = User.objects.create_user(self.login, 'team user', '')
            self.user.first_name = self.name
            self.user.save()
        else:
            self.user.username = self.login
            self.user.first_name = self.name
            self.user.save()
        if not self.join_key:
            self.join_key = generate_key()
        super(Team, self).save(*args, **kwargs)


class TeamMembership(models.Model):
    """Represents a realation between an user and a team.
    """
    user = models.ForeignKey(User)
    team = models.ForeignKey(Team, related_name='members')

    class Meta(object):
        unique_together = ("user", "team")

    def validate_unique(self, *args, **kwargs):
        super(TeamMembership, self).validate_unique(*args, **kwargs)

        query = TeamMembership.objects.filter(user=self.user,
                                              team__contest=self.team.contest)
        # Excluding unsaved object excludes everything see:
        # https://code.djangoproject.com/ticket/25467
        if self.team.pk is not None:
            query = query.exclude(team=self.team)

        if query.exists():
            raise ValidationError(
                    {'user': {"The user is already in another team"}})


teams_list_visibility_options = EnumRegistry()
teams_list_visibility_options.register('PUBLIC', _("Visible for all"))
teams_list_visibility_options.register('YES',
        _("Visible only for registered users"))
teams_list_visibility_options.register('NO', _("Not visible"))


class TeamsConfig(models.Model):
    contest = models.OneToOneField(Contest)
    enabled = models.BooleanField(default=False)
    max_team_size = models.IntegerField(default=3,
                                        validators=[MinValueValidator(1)])
    modify_begin_date = models.DateTimeField(
        verbose_name=_("team modification begin date"), blank=True, null=True)
    modify_end_date = models.DateTimeField(
        verbose_name=_("team modification end date"), blank=True, null=True)
    teams_list_visible = EnumField(teams_list_visibility_options, default='NO',
            verbose_name=_("teams list visibility"))

    class Meta(object):
        verbose_name = _("teams configuration")
        verbose_name_plural = _("teams configurations")
