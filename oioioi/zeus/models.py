import os

from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import submission_statuses
from oioioi.problems.models import Problem
from oioioi.programs.models import TestReport

check_django_app_dependencies(__name__, ['oioioi.testrun'], strict=True)


submission_statuses.register('MSE', _("Outgoing message size limit exceeded"))
submission_statuses.register('MCE', _("Outgoing message count limit exceeded"))


class ZeusProblemData(models.Model):
    problem = models.OneToOneField(Problem, primary_key=True, on_delete=models.CASCADE)
    zeus_id = models.CharField(max_length=255)
    zeus_problem_id = models.IntegerField(default=0)


def make_custom_library_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'testruns/%s/%d/lib%s' % (
        instance.problem_instance.contest_id,
        instance.id,
        os.path.splitext(filename)[1],
    )


class ZeusTestReport(TestReport):
    nodes = models.IntegerField(null=True)
    check_uid = models.CharField(max_length=255)
