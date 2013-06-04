from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Contest


class ContestLogo(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True)
    logo_url = models.CharField(max_length=255, verbose_name=_("URL"))

    class Meta:
        verbose_name = _("contest logo")
        verbose_name_plural = _("contest logo")
