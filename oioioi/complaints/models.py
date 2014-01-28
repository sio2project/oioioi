from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import Contest
from oioioi.contests.date_registration import date_registry


# The view imports participants.models
check_django_app_dependencies(__name__, ['oioioi.participants'])


@date_registry.register('start_date',
                        name_generator=(lambda obj: _("Enable complaints")))
@date_registry.register('end_date',
                        name_generator=(lambda obj: _("Disable complaints")))
class ComplaintsConfig(models.Model):
    contest = models.OneToOneField(Contest,
                        related_name='complaints_config')
    enabled = models.BooleanField(verbose_name=_("enabled"))
    start_date = models.DateTimeField(verbose_name=_("start date"))
    end_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("end date"))

    class Meta(object):
        verbose_name = _("complaints configuration")
        verbose_name_plural = _("complaints configurations")
