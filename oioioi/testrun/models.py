from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.base.fields import EnumField
from oioioi.contests.models import (
    SubmissionReport,
    submission_kinds,
    submission_report_kinds,
    submission_statuses,
)
from oioioi.filetracker.fields import FileField
from oioioi.problems.models import Problem, ProblemInstance
from oioioi.programs.models import ProgramSubmission

submission_statuses.register('TESTRUN_OK', _("No error"))
submission_kinds.register('TESTRUN', _("Test run"))
submission_report_kinds.register('TESTRUN', _("Test run report"))


def make_custom_input_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'testruns/%s/%d/in' % (instance.problem_instance.contest_id, instance.id)


class TestRunProgramSubmission(ProgramSubmission):
    __test__ = False
    input_file = FileField(upload_to=make_custom_input_filename)


def make_custom_output_filename(instance, filename):
    # This code is dead (it's result is ignored) with current implementation
    # of assigning file from filetracker to a FileField.
    submission = instance.submission_report.submission
    return 'testruns/%s/%d/%d-out' % (
        submission.problem_instance.contest_id,
        submission.id,
        instance.submission_report_id,
    )


class TestRunConfig(models.Model):
    """Represents a test run config for problem instance.

    Test run for program is enabled iff this model exits.
    """

    __test__ = False
    problem_instance = models.OneToOneField(
        ProblemInstance,
        verbose_name=_("problem instance"),
        related_name='test_run_config',
        on_delete=models.CASCADE,
    )

    test_runs_limit = models.IntegerField(
        default=settings.DEFAULT_TEST_RUNS_LIMIT, verbose_name=_("test runs limit")
    )

    time_limit = models.IntegerField(verbose_name=_("time limit (ms)"))
    memory_limit = models.IntegerField(verbose_name=_("memory limit (KiB)"))

    class Meta(object):
        verbose_name = _("test run config")
        verbose_name_plural = _("test run configs")


class TestRunReport(models.Model):
    __test__ = False
    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    status = EnumField(submission_statuses)
    comment = models.CharField(max_length=255, blank=True)
    time_used = models.IntegerField(blank=True)
    test_time_limit = models.IntegerField(null=True, blank=True)
    output_file = FileField(upload_to=make_custom_output_filename)
