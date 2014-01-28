from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest
from oioioi.contests.date_registration import date_registry


class ExclusivenessConfigManager(models.Manager):
    def get_active(self, timestamp):
        condition = Q(start_date__lte=timestamp, end_date__isnull=True) \
            | Q(start_date__lte=timestamp, end_date__gte=timestamp)
        condition &= Q(enabled=True)
        return self.get_query_set().filter(condition)

    def get_active_between(self, start, end):
        if not (end is None or start <= end):
            raise ValueError("The start date should precede the end date")
        neg_condition = Q(end_date__isnull=False, end_date__lt=start)
        neg_condition |= Q(enabled=False)
        if end is not None:
            neg_condition |= Q(start_date__gt=end)
        return self.get_query_set().exclude(neg_condition)


@date_registry.register('start_date',
                        name_generator=(lambda obj: _("Enable exclusiveness")))
@date_registry.register('end_date',
                        name_generator=(lambda obj:
                                        _("Disable exclusiveness")))
class ExclusivenessConfig(models.Model):
    """Represents an exclusiveness config for a contest.

       If it is enabled it becomes active on the date specified by
       ``start_date`` and stays active until the date specified by
       ``end_date``.
    """
    contest = models.OneToOneField(Contest)
    enabled = models.BooleanField(default=True, verbose_name=_("enabled"))
    start_date = models.DateTimeField(default=timezone.now,
                                      verbose_name=_("start date"))
    end_date = models.DateTimeField(blank=True, null=True,
                                    verbose_name=_("end date"))

    objects = ExclusivenessConfigManager()

    class Meta(object):
        verbose_name = _("exclusiveness config")
        verbose_name_plural = _("exclusiveness configs")

    def __unicode__(self):
        return u'%s (%s): %s - %s' % (self.contest,
                                      'enabled' if self.enabled
                                              else 'disabled',
                                      self.start_date, self.end_date)

    def clean(self):
        if self.end_date is not None and self.start_date > self.end_date:
            raise ValidationError(_("The start date should"
                                    " precede the end date"))
