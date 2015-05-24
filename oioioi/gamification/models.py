from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.gamification.constants import CODE_SHARING_PREFERENCES_DEFAULT, \
    Lvl1TaskExp, Lvl2TaskExp, Lvl3TaskExp, Lvl4TaskExp, Lvl5TaskExp


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


class ProblemDifficulty(models.Model):
    problem = models.OneToOneField('problems.Problem')
    difficulty = models.SmallIntegerField(null=True, blank=True)

    @property
    def localized_name(self):
        """Returns a string represation of Problem's difficulty, localized"""
        from oioioi.gamification.difficulty import DIFFICULTY
        if self.difficulty == DIFFICULTY.TRIVIAL:
            return _("trivial")
        elif self.difficulty == DIFFICULTY.EASY:
            return _("easy")
        elif self.difficulty == DIFFICULTY.MEDIUM:
            return _("medium")
        elif self.difficulty == DIFFICULTY.HARD:
            return _("hard")
        elif self.difficulty == DIFFICULTY.IMPOSSIBLE:
            return _("impossible")
        return _("none")

    @property
    def experience(self):
        """Returns experience for this problem"""
        from oioioi.gamification.difficulty import DIFFICULTY
        if self.difficulty == DIFFICULTY.TRIVIAL:
            return Lvl1TaskExp
        elif self.difficulty == DIFFICULTY.EASY:
            return Lvl2TaskExp
        elif self.difficulty == DIFFICULTY.MEDIUM:
            return Lvl3TaskExp
        elif self.difficulty == DIFFICULTY.HARD:
            return Lvl4TaskExp
        elif self.difficulty == DIFFICULTY.IMPOSSIBLE:
            return Lvl5TaskExp
        return 0
