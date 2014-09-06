from nose.tools import nottest
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from oioioi.base.fields import EnumRegistry, EnumField
from oioioi.problems.models import Problem, make_problem_filename
from oioioi.filetracker.fields import FileField
from oioioi.contests.models import Submission, SubmissionReport, \
        submission_statuses, submission_report_kinds, ProblemInstance, \
        submission_kinds
from oioioi.contests.fields import ScoreField

import os.path

test_kinds = EnumRegistry()
test_kinds.register('NORMAL', _("Normal test"))
test_kinds.register('EXAMPLE', _("Example test"))


def validate_time_limit(value):
    if value is None or value <= 0:
        raise ValidationError(_("Time limit must be a positive number."))


@nottest
class Test(models.Model):
    problem = models.ForeignKey(Problem)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    input_file = FileField(upload_to=make_problem_filename,
            verbose_name=_("input"), null=True, blank=True)
    output_file = FileField(upload_to=make_problem_filename,
            verbose_name=_("output/hint"), null=True, blank=True)
    kind = EnumField(test_kinds, verbose_name=_("kind"))
    group = models.CharField(max_length=30, verbose_name=_("group"))
    time_limit = models.IntegerField(verbose_name=_("time limit (ms)"),
            null=True, blank=False, validators=[validate_time_limit])
    memory_limit = models.IntegerField(verbose_name=_("memory limit (KiB)"),
            null=True, blank=True)
    max_score = models.IntegerField(verbose_name=_("score"),
            default=10)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class Meta(object):
        ordering = ['order']
        verbose_name = _("test")
        verbose_name_plural = _("tests")
        unique_together = ('problem', 'name')


class OutputChecker(models.Model):
    problem = models.OneToOneField(Problem)
    exe_file = FileField(upload_to=make_problem_filename,
            null=True, blank=True, verbose_name=_("checker executable file"))

    class Meta(object):
        verbose_name = _("output checker")
        verbose_name_plural = _("output checkers")


class LibraryProblemData(models.Model):
    problem = models.OneToOneField(Problem)
    libname = models.CharField(max_length=30, verbose_name=_("libname"),
            help_text=_("Filename library should be given during compilation"))

    class Meta(object):
        verbose_name = _("library problem data")
        verbose_name_plural = _("library problem data")


@receiver(post_save, sender=Problem)
def _add_output_checker_to_problem(sender, instance, created, **kwargs):
    if created:
        OutputChecker(problem=instance).save()

model_solution_kinds = EnumRegistry()
model_solution_kinds.register('NORMAL', _("Model solution"))
model_solution_kinds.register('SLOW', _("Slow solution"))
model_solution_kinds.register('INCORRECT', _("Incorrect solution"))


class ModelSolutionsManager(models.Manager):
    def recreate_model_submissions(self, problem_instance):
        with transaction.atomic():
            for model_submission in ModelProgramSubmission.objects.filter(
                    problem_instance=problem_instance):
                model_submission.delete()
        if not problem_instance.round:
            return
        controller = problem_instance.contest.controller
        for model_solution in self.filter(problem=problem_instance.problem):
            with transaction.atomic():
                submission = ModelProgramSubmission(
                        model_solution=model_solution,
                        problem_instance=problem_instance,
                        source_file=model_solution.source_file,
                        kind='IGNORED')
                submission.save()
            controller.judge(submission, is_rejudge=True)


class ModelSolution(models.Model):
    objects = ModelSolutionsManager()

    problem = models.ForeignKey(Problem)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    source_file = FileField(upload_to=make_problem_filename,
            verbose_name=_("source"))
    kind = EnumField(model_solution_kinds, verbose_name=_("kind"))
    order_key = models.IntegerField(default=0)

    @property
    def short_name(self):
        return self.name.rsplit('.', 1)[0]


@receiver(pre_save, sender=ProblemInstance)
def _decide_if_autocreate_model_submissions_for_problem_instance(sender,
        instance, raw, **kwargs):
    instance.create_model_submissions = False
    if raw or instance.round is None:
        return
    try:
        old = ProblemInstance.objects.get(pk=instance.pk)
        if old.round != instance.round:
            instance.create_model_submissions = True
    except ProblemInstance.DoesNotExist:
        instance.create_model_submissions = True


@receiver(post_save, sender=ProblemInstance)
def _autocreate_model_submissions_for_problem_instance(sender, instance,
        created, raw, **kwargs):
    if instance.create_model_submissions:
        ModelSolution.objects.recreate_model_submissions(instance)


@receiver(post_save, sender=ModelSolution)
def _autocreate_model_submissions_for_model_solutions(sender, instance,
        created, raw, **kwargs):
    if created and not raw:
        pis = ProblemInstance.objects.filter(problem=instance.problem)
        for pi in pis:
            ModelSolution.objects.recreate_model_submissions(pi)


def make_submission_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'submissions/%s/%d%s' % (instance.problem_instance.contest.id,
            instance.id, os.path.splitext(filename)[1])


class ProgramSubmission(Submission):
    source_file = FileField(upload_to=make_submission_filename)
    source_length = models.IntegerField(verbose_name=_("Source code length"),
                                        blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.source_file:
            self.source_length = self.source_file.size
        super(ProgramSubmission, self).save(*args, **kwargs)


class ModelProgramSubmission(ProgramSubmission):
    model_solution = models.ForeignKey(ModelSolution)

submission_statuses.register('CE', _("Compilation failed"))
submission_statuses.register('RE', _("Runtime error"))
submission_statuses.register('WA', _("Wrong answer"))
submission_statuses.register('TLE', _("Time limit exceeded"))
submission_statuses.register('MLE', _("Memory limit exceeded"))
submission_statuses.register('OLE', _("Output limit exceeded"))
submission_statuses.register('SE', _("System error"))
submission_statuses.register('RV', _("Rule violation"))

submission_statuses.register('INI_OK', _("Initial tests: OK"))
submission_statuses.register('INI_ERR', _("Initial tests: failed"))

submission_kinds.register('USER_OUTS', _("Generate user out"))

submission_report_kinds.register('INITIAL', _("Initial report"))
submission_report_kinds.register('NORMAL', _("Normal report"))
submission_report_kinds.register('FULL', _("Full report"))
submission_report_kinds.register('HIDDEN',
                                 _("Hidden report (for admins only)"))
submission_report_kinds.register('USER_OUTS', _("Report with user out"))


class CompilationReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses)
    compiler_output = models.TextField()


def make_output_filename(instance, filename):
    # This code is dead (it's result is ignored) with current implementation
    # of assigning file from filetracker to a FileField.
    submission = instance.submission_report.submission
    return 'userouts/%s/%d/%d-out' % (submission.problem_instance.contest.id,
            submission.id, instance.submission_report.id)


@nottest
class TestReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses)
    comment = models.CharField(max_length=255, blank=True)
    score = ScoreField(null=True, blank=True)
    time_used = models.IntegerField(blank=True)
    output_file = FileField(upload_to=make_output_filename, null=True,
                            blank=True)

    test = models.ForeignKey(Test, blank=True, null=True,
            on_delete=models.SET_NULL)
    test_name = models.CharField(max_length=30)
    test_group = models.CharField(max_length=30)
    test_time_limit = models.IntegerField(null=True, blank=True)
    test_max_score = models.IntegerField(null=True, blank=True)


class GroupReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    group = models.CharField(max_length=30)
    score = ScoreField(null=True, blank=True)
    max_score = ScoreField(null=True, blank=True)
    status = EnumField(submission_statuses)


class ReportActionsConfig(models.Model):
    problem = models.OneToOneField(Problem,
                                   verbose_name=_("problem instance"),
                                   related_name='report_actions_config',
                                   primary_key=True
                                   )
    can_user_generate_outs = models.BooleanField(default=False,
             verbose_name=_("Allow users to generate their outs on tests "
                            "from visible reports."))


class UserOutGenStatus(models.Model):
    testreport = models.OneToOneField(TestReport, primary_key=True,
                                      related_name='userout_status')
    status = EnumField(submission_statuses, default='?')
    visible_for_user = models.BooleanField(default=True)
