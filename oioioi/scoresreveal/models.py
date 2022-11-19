from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.contests.models import ProblemInstance, Submission


class ScoreReveal(models.Model):
    submission = models.OneToOneField(
        Submission,
        related_name='revealed',
        verbose_name=_("submission"),
        on_delete=models.CASCADE,
    )

    class Meta(object):
        verbose_name = _("score reveal")
        verbose_name_plural = _("score reveals")


class ScoreRevealConfig(models.Model):
    problem_instance = models.OneToOneField(
        ProblemInstance,
        verbose_name=_("problem instance"),
        related_name='scores_reveal_config',
        on_delete=models.CASCADE,
    )
    reveal_limit = models.IntegerField(
        verbose_name=_("reveal limit"),
        help_text=_("If empty, all submissions are revealed automatically."),
        blank=True,
        null=True,
    )
    disable_time = models.IntegerField(
        blank=True, null=True, verbose_name=_("disable for last minutes of the round")
    )

    class Meta(object):
        verbose_name = _("score reveal config")
        verbose_name_plural = _("score reveal configs")
