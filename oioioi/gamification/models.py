from django.db import models
from django.contrib.auth.models import User


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
