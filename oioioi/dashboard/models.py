from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest


class DashboardMessage(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("message"), blank=True)

    class Meta(object):
        verbose_name = _("dashboard message")
        verbose_name_plural = _("dashboard messages")
