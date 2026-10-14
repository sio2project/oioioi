from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.contests.models import Contest, ProblemInstance, Submission


class ScoreReveal(models.Model):
    submission = models.OneToOneField(
        Submission,
        related_name="revealed",
        verbose_name=_("submission"),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("score reveal")
        verbose_name_plural = _("score reveals")


class ScoreRevealConfig(models.Model):
    problem_instance = models.OneToOneField(
        ProblemInstance,
        verbose_name=_("problem instance"),
        related_name="scores_reveal_config",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    contest = models.OneToOneField(
        Contest,
        verbose_name=_("contest"),
        related_name="scores_reveal_config",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    reveal_limit = models.IntegerField(
        verbose_name=_("reveal limit"),
        help_text=_("If empty, all submissions are revealed automatically. A value of 0 disables reveals."),
        blank=True,
        null=True,
    )
    disable_time = models.IntegerField(blank=True, null=True, verbose_name=_("disable for last minutes of the round"))

    class Meta:
        verbose_name = _("score reveal config")
        verbose_name_plural = _("score reveal configs")

    def clean(self):
        super().clean()
        if not self.problem_instance and not self.contest:
            raise ValidationError(_("ScoresRevealConfig must be attached to either a contest or a problem instance."))
        if self.problem_instance and self.contest:
            raise ValidationError(_("ScoresRevealConfig cannot be attached to both a contest and a problem instance simultaneously."))
