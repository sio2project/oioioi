import os

from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import EnumField
from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import submission_report_kinds, submission_statuses
from oioioi.filetracker.fields import FileField
from oioioi.problems.models import Problem
from oioioi.testrun.models import TestRunReport, TestRunProgramSubmission


check_django_app_dependencies(__name__, ['oioioi.testrun'], strict=True)


submission_statuses.register('MSE', _("Outgoing message size limit exceeded"))
submission_statuses.register('MCE', _("Outgoing message count limit exceeded"))


class ZeusProblemData(models.Model):
    problem = models.OneToOneField(Problem, primary_key=True)
    zeus_id = models.CharField(max_length=255)
    zeus_problem_id = models.IntegerField(default=0)


class ZeusAsyncJob(models.Model):
    check_uid = models.IntegerField(primary_key=True)
    kind = EnumField(submission_report_kinds)
    environ = models.TextField()


def make_custom_library_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'testruns/%s/%d/lib%s' % (instance.problem_instance.contest.id,
            instance.id, os.path.splitext(filename)[1])


class ZeusTestRunProgramSubmission(TestRunProgramSubmission):
    library_file = FileField(upload_to=make_custom_library_filename, null=True)


class ZeusTestRunReport(TestRunReport):
    full_out_size = models.IntegerField()
    full_out_handle = models.CharField(max_length=255, blank=True)


class ZeusFetchSeq(models.Model):
    zeus_id = models.CharField(max_length=255, primary_key=True)
    next_seq = models.IntegerField(default=0)
