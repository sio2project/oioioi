from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import Contest
from oioioi.ipdnsauth.models import IpToUser
from oioioi.participants.models import Region

check_django_app_dependencies(__name__, ['oioioi.participants', 'oioioi.ipdnsauth'])


class IpAuthSyncConfigManager(models.Manager):
    def get_active(self, timestamp):
        return self.get_queryset().filter(
            start_date__lte=timestamp, end_date__gte=timestamp, enabled=True
        )


@date_registry.register(
    'start_date', name_generator=(lambda obj: _("Enable IP authentication sync"))
)
@date_registry.register(
    'end_date', name_generator=(lambda obj: _("Disable IP authentication sync"))
)
class IpAuthSyncConfig(models.Model):
    contest = models.OneToOneField(Contest, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True, verbose_name=_("enabled"))
    start_date = models.DateTimeField(
        default=timezone.now, verbose_name=_("start date")
    )
    end_date = models.DateTimeField(verbose_name=_("end date"))

    objects = IpAuthSyncConfigManager()

    class Meta(object):
        verbose_name = _("IP authentication sync config")
        verbose_name_plural = _("IP authentication sync configs")

    def __str__(self):
        return u'%s (%s): %s - %s' % (
            self.contest,
            u'enabled' if self.enabled else u'disabled',
            self.start_date,
            self.end_date,
        )

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("The start date should precede the end date"))


class IpAuthSyncedUser(models.Model):
    entry = models.OneToOneField(IpToUser, on_delete=models.CASCADE)


class IpAuthSyncRegionMessages(models.Model):
    region = models.OneToOneField(Region, on_delete=models.CASCADE)
    warnings = models.TextField(blank=True, verbose_name=_("Warnings"))
    mapping = models.TextField(blank=True, verbose_name=_("Mapping"))

    class Meta(object):
        verbose_name = _("IP authentication sync messages")
        verbose_name_plural = _("IP authentication sync messages")
