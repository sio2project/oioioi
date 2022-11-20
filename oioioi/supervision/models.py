from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Round


class Group(models.Model):
    """
    Group of people to use with Supervision.
    """
    name = models.CharField(max_length=50, verbose_name=_("name"))
    members = models.ManyToManyField(
        User,
        through='Membership',
        through_fields=('group', 'user'),
    )

    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")

    def __unicode__(self):
        return str("{}".format(self.name))


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("user"))
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name=_("group"))
    is_present = models.BooleanField(default=False, verbose_name=_("present"))

    class Meta:
        unique_together = ('user', 'group')
        verbose_name = _("Members")
        verbose_name_plural = _("Members")

    def __unicode__(self):
        present = "present"
        if not present:
            present = "not " + present

        return str("{} {} {} {} {}".format(
            self.user,
            _("inside"),
            self.group,
            _("is"),
            _(present)
        ))


class Supervision(models.Model):
    """
    Store groups and their supervisions. Is valid from start_date to end_date.
    I will have to think about Celery task to clear it.
    """
    group = models.ForeignKey(Group, verbose_name=_("group"), on_delete=models.CASCADE)
    round = models.ForeignKey(Round, verbose_name=_("round"), on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now, verbose_name=_("start date"))
    end_date = models.DateTimeField(default=timezone.now, verbose_name=_("end date"))

    class Meta(object):
        unique_together = ('group', 'round')
        verbose_name = _("supervision")
        verbose_name_plural = _("supervisions")

    def __unicode__(self):
        return str("{} {} {}".format(
            self.group,
            _("inside"),
            self.round
        ))
