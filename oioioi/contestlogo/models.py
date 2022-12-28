import os.path

from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _

from oioioi.contests.models import Contest
from oioioi.filetracker.fields import FileField


def make_logo_filename(instance, filename):
    return 'logo/%s/%s' % (
        instance.contest.id,
        get_valid_filename(os.path.basename(filename)),
    )


class ContestLogo(models.Model):
    contest = models.OneToOneField(
        Contest, verbose_name=_("contest"), primary_key=True, on_delete=models.CASCADE
    )
    image = FileField(upload_to=make_logo_filename, verbose_name=_("logo image"))
    updated_at = models.DateTimeField(default=timezone.now)
    link = models.URLField(
        blank=True, null=True, verbose_name=_("external contest webpage url")
    )

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        return super(ContestLogo, self).save(*args, **kwargs)

    @property
    def filename(self):
        return os.path.split(self.image.name)[1]

    class Meta(object):
        verbose_name = _("contest logo")
        verbose_name_plural = _("contest logo")


def make_icon_filename(instance, filename):
    return 'icons/%s/%s' % (
        instance.contest_id,
        get_valid_filename(os.path.basename(filename)),
    )


class ContestIcon(models.Model):
    contest = models.ForeignKey(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    image = FileField(upload_to=make_icon_filename, verbose_name=_("icon image"))
    updated_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        return super(ContestIcon, self).save(*args, **kwargs)

    @property
    def filename(self):
        return os.path.split(self.image.name)[1]

    class Meta(object):
        verbose_name = _("contest icon")
        verbose_name_plural = _("contest icons")
