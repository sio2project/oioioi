from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.filetracker.fields import FileField
from oioioi.problems.models import Problem, make_problem_filename


class Interactor(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    exe_file = FileField(
        upload_to=make_problem_filename,
        null=True,
        blank=True,
        verbose_name=_("interactive executable file"),
    )

    class Meta(object):
        verbose_name = _("interactive executable file")
        verbose_name_plural = _("interactive executable files"),


class InteractiveTaskInfo(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    num_processes = models.IntegerField(
        verbose_name=_("number of user's processes to run"), default=1
    )
