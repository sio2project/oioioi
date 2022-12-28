from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.validators import validate_whitespaces
from oioioi.contests.models import Contest, Submission


class Disqualification(models.Model):
    contest = models.ForeignKey(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.CASCADE)
    # Leave submission empty to make contest-wide disqualification
    submission = models.ForeignKey(
        Submission,
        null=True,
        blank=True,
        verbose_name=_("submission"),
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        max_length=255,
        validators=[MaxLengthValidator(255), validate_whitespaces],
        verbose_name=_("title"),
    )
    content = models.TextField(verbose_name=_("content"))
    guilty = models.BooleanField(default=True)

    class Meta(object):
        verbose_name = _("disqualification")
        verbose_name_plural = _("disqualifications")

    def clean(self):
        if self.submission and self.submission.user != self.user:
            raise ValidationError(_("The submission does not match the user."))

    def save(self, *args, **kwargs):
        if self.submission:
            assert self.contest_id == self.submission.problem_instance.contest_id
            assert self.user_id == self.submission.user_id

        super(Disqualification, self).save(*args, **kwargs)


class DisqualificationsConfig(models.Model):
    contest = models.OneToOneField(
        Contest, related_name='disqualifications_config', on_delete=models.CASCADE
    )

    info = models.TextField(
        verbose_name=_(
            "information displayed on dashboard for every disqualified participant"
        )
    )

    class Meta(object):
        verbose_name = _("diqualifications configuration")
        verbose_name_plural = _("disqualifications configurations")
