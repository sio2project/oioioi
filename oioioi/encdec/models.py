from django.db import models

from django.utils.translation import gettext_lazy as _

from functools import wraps

from oioioi.base.fields import EnumField
from oioioi.contests.fields import ScoreField
from oioioi.contests.models import (
    ProblemInstance,
    SubmissionReport,
    submission_statuses,
)
from oioioi.filetracker.fields import FileField
from oioioi.problems.models import Problem, make_problem_filename
from oioioi.programs.models import (
    test_kinds,
    validate_memory_limit,
    validate_time_limit,
)


submission_statuses.register('SKIP', _('Skipped'))


class EncdecTest(models.Model):
    __test__ = False
    problem_instance = models.ForeignKey(ProblemInstance, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    input_file = FileField(
        upload_to=make_problem_filename, verbose_name=_("input"), null=True, blank=True
    )
    hint_file = FileField(
        upload_to=make_problem_filename, verbose_name=_("hint"), null=True, blank=True
    )
    kind = EnumField(test_kinds, verbose_name=_("kind"))
    group = models.CharField(max_length=30, verbose_name=_("group"))
    encoder_time_limit = models.IntegerField(
        verbose_name=_("encoder time limit (ms)"),
        null=True,
        blank=False,
        validators=[validate_time_limit],
    )
    decoder_time_limit = models.IntegerField(
        verbose_name=_("decoder time limit (ms)"),
        null=True,
        blank=False,
        validators=[validate_time_limit],
    )
    encoder_memory_limit = models.IntegerField(
        verbose_name=_("encoder memory limit (KiB)"),
        null=True,
        blank=True,
        validators=[validate_memory_limit],
    )
    decoder_memory_limit = models.IntegerField(
        verbose_name=_("decoder_memory limit (KiB)"),
        null=True,
        blank=True,
        validators=[validate_memory_limit],
    )
    max_score = models.IntegerField(verbose_name=_("score"), default=10)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    @property
    def problem(self):
        return self.problem_instance.problem

    @property
    def total_time_limit(self):
        return self.encoder_time_limit + self.decoder_time_limit

    def __str__(self):
        return str(self.name)

    class Meta(object):
        ordering = ['order']
        verbose_name = _("test")
        verbose_name_plural = _("tests")
        unique_together = ('problem_instance', 'name')


class LanguageOverrideForEncdecTest(models.Model):
    test = models.ForeignKey(EncdecTest, on_delete=models.CASCADE)
    encoder_time_limit = models.IntegerField(
        verbose_name=_("encoder time limit (ms)"),
        null=True,
        blank=False,
        validators=[validate_time_limit],
    )
    decoder_time_limit = models.IntegerField(
        verbose_name=_("decoder time limit (ms)"),
        null=True,
        blank=False,
        validators=[validate_time_limit],
    )
    encoder_memory_limit = models.IntegerField(
        verbose_name=_("encoder memory limit (KiB)"),
        null=True,
        blank=True,
        validators=[validate_memory_limit],
    )
    decoder_memory_limit = models.IntegerField(
        verbose_name=_("decoder memory limit (KiB)"),
        null=True,
        blank=True,
        validators=[validate_memory_limit],
    )
    language = models.CharField(max_length=30, verbose_name=_("language"))

    class Meta(object):
        ordering = ['test__order']
        verbose_name = _("encoder-decoder test limit override")
        verbose_name_plural = _("encoder-decoder tests limit overrides")
        unique_together = ('test', 'language')


class EncdecChannel(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    exe_file = FileField(
        upload_to=make_problem_filename,
        null=True,
        blank=True,
        verbose_name=_("encoder-decoder channel executable file"),
    )

    class Meta(object):
        verbose_name = _("encoder-decoder channel")
        verbose_name_plural = _("encoder-decoder channels")


class EncdecChecker(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    exe_file = FileField(
        upload_to=make_problem_filename,
        null=True,
        blank=True,
        verbose_name=_("encoder-decoder checker executable file"),
    )

    class Meta(object):
        verbose_name = _("encoder-decoder output checker")
        verbose_name_plural = _("encoder-decoder output checkers")


def make_encoder_output_filename(instance, filename):
    # This code is dead (it's result is ignored) with current implementation
    # of assigning file from filetracker to a FileField.

    # My honest take:
    # So why the fuck it is still here? Just to suffer?
    submission = instance.submission_report.submission
    return 'userouts/%s/%d/%d-encoder-out' % (
        submission.problem_instance.contest.id,
        submission.id,
        instance.submission_report.id,
    )


def make_decoder_output_filename(instance, filename):
    # This code is dead (it's result is ignored) with current implementation
    # of assigning file from filetracker to a FileField.

    # My honest take:
    # So why the fuck it is still here? Just to suffer?
    submission = instance.submission_report.submission
    return 'userouts/%s/%d/%d-decoder-out' % (
        submission.problem_instance.contest.id,
        submission.id,
        instance.submission_report.id,
    )


class EncdecTestReport(models.Model):
    __test__ = False
    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    encoder_status = EnumField(submission_statuses)
    decoder_status = EnumField(submission_statuses)
    comment = models.CharField(max_length=255, blank=True)
    score = ScoreField(null=True, blank=True)
    max_score = ScoreField(null=True, blank=True)
    encoder_time_used = models.IntegerField(blank=True)
    decoder_time_used = models.IntegerField(blank=True)
    encoder_output_file = FileField(upload_to=make_encoder_output_filename, null=True, blank=True)
    decoder_output_file = FileField(upload_to=make_decoder_output_filename, null=True, blank=True)

    test = models.ForeignKey(EncdecTest, blank=True, null=True, on_delete=models.SET_NULL)
    test_name = models.CharField(max_length=30)
    test_group = models.CharField(max_length=30)
    test_encoder_time_limit = models.IntegerField(null=True, blank=True)
    test_decoder_time_limit = models.IntegerField(null=True, blank=True)

    @property
    def has_all_outputs(self):
        return bool(self.encoder_output_file) and bool(self.decoder_output_file)


class EncdecUserOutGenStatus(models.Model):
    testreport = models.OneToOneField(
        EncdecTestReport,
        primary_key=True,
        related_name='userout_status',
        on_delete=models.CASCADE,
    )
    status = EnumField(submission_statuses, default='?')
    visible_for_user = models.BooleanField(default=True)
