from django.db import models
from django.contrib.auth.models import User
from oioioi.gamification.constants import CODE_SHARING_PREFERENCES_DEFAULT


class CachedExperienceSourceID(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=50)
    cache_id = models.IntegerField()
    value = models.IntegerField()


class CachedExperienceSourceTotal(models.Model):
    name = models.CharField(max_length=50)
    user = models.ForeignKey(User)
    value = models.IntegerField()


class FriendProxy(models.Model):
    user = models.OneToOneField(User)
    friends = models.ManyToManyField('self')


class FriendshipRequest(models.Model):
    sender = models.ForeignKey(FriendProxy,
                               related_name='sent_requests')
    recipient = models.ForeignKey(FriendProxy,
                                  related_name='incoming_requests')

    class Meta(object):
        unique_together = ('sender', 'recipient')


class CodeSharingSettingsManager(models.Manager):
    def sharing_allowed(self, user):
        return self.get_or_create(
            user=user,
            defaults={'code_share_allowed': CODE_SHARING_PREFERENCES_DEFAULT}
        )[0].code_share_allowed


class CodeSharingSettings(models.Model):
    user = models.OneToOneField(User, unique=True, null=False, blank=False)
    code_share_allowed = models.BooleanField(null=False, blank=False,
                                             default=False)

    objects = CodeSharingSettingsManager()
