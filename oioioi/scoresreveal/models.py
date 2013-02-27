from django.db import models
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Submission
from oioioi.problems.models import Problem

class ScoreReveal(models.Model):
    submission = models.OneToOneField(Submission, related_name='revealed',
                                      verbose_name=_("submission"))

    class Meta:
        verbose_name = _("score reveal")
        verbose_name_plural = _("score reveals")

class ScoreRevealConfig(models.Model):
    problem = models.OneToOneField(Problem,
                                   verbose_name=_("problem"),
                                   related_name='scores_reveal_config')
    reveal_limit = models.IntegerField(verbose_name=_("Reveal limit"))
    disable_time = models.IntegerField(blank=True, null=True,
        verbose_name=_("disable for last minutes of the round"))

    class Meta:
        verbose_name = _("score reveal config")
        verbose_name_plural = _("score reveal configs")