from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Submission


class VoluntarySolutionPublication(models.Model):
    submission = models.OneToOneField(Submission, primary_key=True,
                                      related_name='publication',
                                      verbose_name=_("submission"),
                                      on_delete=models.CASCADE)

    class Meta(object):
        verbose_name = _("voluntary solution publication")
        verbose_name_plural = _("voluntary solution publications")
