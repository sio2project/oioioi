from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.db.models import ProtectedError
from django.db.models.signals import post_delete, pre_save

from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import generate_key
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Contest

check_django_app_dependencies(__name__, ['oioioi.teachers'])



class UserGroup(models.Model):
    """Group of user which can be moved around contests by teachers"""

    name = models.CharField(max_length=255, verbose_name=_("name"))
    owners = models.ManyToManyField(User, related_name='owned_usergroups')
    members = models.ManyToManyField(User, blank=True, related_name='usergroups')
    contests = models.ManyToManyField(Contest, blank=True, related_name='usergroups')

    addition_config = models.ForeignKey(
        'ActionConfig', on_delete=models.PROTECT, related_name='as_addition_configs'
    )
    sharing_config = models.ForeignKey(
        'ActionConfig', on_delete=models.PROTECT, related_name='as_sharing_configs'
    )

    def __str__(self):
        return str(self.name)


class ActionConfig(models.Model):
    enabled = models.BooleanField(default=False)
    key = models.CharField(max_length=40, unique=True)

    def __init__(self, *args, **kwargs):
        super(ActionConfig, self).__init__(*args, **kwargs)

        if not self.key:
            self.key = generate_key()


def add_default_configs_if_empty(instance, **kwargs):
    if instance.addition_config_id is None:
        addition_config = ActionConfig()
        addition_config.save()
        instance.addition_config = addition_config

    if instance.sharing_config_id is None:
        sharing_config = ActionConfig()
        sharing_config.save()
        instance.sharing_config = sharing_config


pre_save.connect(receiver=add_default_configs_if_empty, sender=UserGroup)


def delete_isolated_configs(instance, **kwargs):
    # We should delete these configs if they are no longer connected to anything.
    try:
        instance.addition_config.delete()
    except ProtectedError:
        pass

    try:
        instance.sharing_config.delete()
    except ProtectedError:
        pass


post_delete.connect(receiver=delete_isolated_configs, sender=UserGroup)


class UserGroupRanking(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user_group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)

    class Meta(object):
        unique_together = ('contest', 'user_group')

    def __str__(self):
        return str(self.user_group.name)
