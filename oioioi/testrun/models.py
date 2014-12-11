from nose.tools import nottest
from django.db import models
from oioioi.contests.models import submission_kinds, SubmissionReport, \
    submission_statuses, submission_report_kinds
from django.utils.translation import ugettext_lazy as _
from oioioi.programs.models import ProgramSubmission
from oioioi.filetracker.fields import FileField
from oioioi.base.fields import EnumField
from oioioi.problems.models import Problem

submission_statuses.register('TESTRUN_OK', _("No error"))
submission_kinds.register('TESTRUN', _("Test run"))
submission_report_kinds.register('TESTRUN', _("Test run report"))


@nottest
class TestRunConfig(models.Model):
    """Represents a test run config for problem.

       Test run for program is enabled iff this model exits.
    """
    problem = models.OneToOneField(Problem,
                        verbose_name=_("problem"),
                        related_name='test_run_config')

    time_limit = models.IntegerField(verbose_name=_("time limit (ms)"),
            null=True, blank=True)
    memory_limit = models.IntegerField(verbose_name=_("memory limit (KiB)"),
            null=True, blank=True)

    class Meta(object):
        verbose_name = _("test run config")
        verbose_name_plural = _("test run configs")


def make_custom_input_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'testruns/%s/%d/in' % (instance.problem_instance.contest.id,
            instance.id)


@nottest
class TestRunProgramSubmission(ProgramSubmission):
    input_file = FileField(upload_to=make_custom_input_filename)


def make_custom_output_filename(instance, filename):
    # This code is dead (it's result is ignored) with current implementation
    # of assigning file from filetracker to a FileField.
    submission = instance.submission_report.submission
    return 'testruns/%s/%d/%d-out' % (submission.problem_instance.contest.id,
            submission.id, instance.submission_report.id)


@nottest
class TestRunReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses)
    comment = models.CharField(max_length=255, blank=True)
    time_used = models.IntegerField(blank=True)
    test_time_limit = models.IntegerField(null=True, blank=True)
    output_file = FileField(upload_to=make_custom_output_filename)
