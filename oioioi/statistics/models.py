from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Contest
from oioioi.contests.date_registration import date_registry


@date_registry.register('visibility_date',
               name_generator=(lambda obj: _("Show statistics")))
class StatisticsConfig(models.Model):
    contest = models.OneToOneField(Contest,
                        related_name='statistics_config')
    visible_to_users = models.BooleanField(verbose_name=_("visible to users"),
                                           default=False)
    visibility_date = models.DateTimeField(verbose_name=_("visibility date"))

    class Meta(object):
        verbose_name = _("statistics configuration")
        verbose_name_plural = _("statistics configurations")
