from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Contest


class ComplaintsConfig(models.Model):
    contest = models.OneToOneField(Contest,
                        related_name='complaints_config')
    enabled = models.BooleanField(verbose_name=_("enabled"))
    start_date = models.DateTimeField(verbose_name=_("start date"))
    end_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("end date"))

    class Meta:
        verbose_name = _("complaints configuration")
        verbose_name_plural = _("complaints configurations")
