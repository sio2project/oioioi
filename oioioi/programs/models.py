import os.path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models, transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from django.utils.translation import gettext_lazy as _

from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.contests.fields import ScoreField
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Submission,
    SubmissionReport,
    submission_kinds,
    submission_report_kinds,
    submission_statuses,
)
from oioioi.filetracker.fields import FileField
from oioioi.problems.models import Problem, make_problem_filename
from oioioi.programs.problem_instance_utils import get_language_by_extension

execution_mode_options = EnumRegistry()
execution_mode_options.register('AUTO', _("Auto"))
execution_mode_options.register('cpu', _("Real CPU"))
execution_mode_options.register('sio2jail', _("SIO2Jail"))


class ProgramsConfig(models.Model):
    contest = models.OneToOneField(
        Contest, related_name='programs_config', on_delete=models.CASCADE
    )
    execution_mode = EnumField(
        execution_mode_options,
        default='AUTO',
        verbose_name=_("execution mode"),
        help_text=_(
            "If set to Auto, the execution mode is determined "
            "according to the type of the contest."
        ),
    )

    class Meta(object):
        verbose_name = _("programs configuration")
        verbose_name_plural = _("programs configurations")


test_kinds = EnumRegistry()
test_kinds.register('NORMAL', _("Normal test"))
test_kinds.register('EXAMPLE', _("Example test"))


def validate_time_limit(value):
    if value is None or value <= 0:
        raise ValidationError(_("Time limit must be a positive number."))


def validate_memory_limit(value):
    if value is None or value <= 0:
        raise ValidationError(_("Memory limit must be a positive number."))
    if value > settings.MAX_MEMORY_LIMIT_FOR_TEST:
        raise ValidationError(
            _(
                "Memory limit mustn't be greater than %dKiB."
                % settings.MAX_MEMORY_LIMIT_FOR_TEST
            )
        )



class Test(models.Model):
    __test__ = False
    problem_instance = models.ForeignKey(ProblemInstance, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    input_file = FileField(
        upload_to=make_problem_filename, verbose_name=_("input"), null=True, blank=True
    )
    output_file = FileField(
        upload_to=make_problem_filename,
        verbose_name=_("output/hint"),
        null=True,
        blank=True,
    )
    kind = EnumField(test_kinds, verbose_name=_("kind"))
    group = models.CharField(max_length=30, verbose_name=_("group"))
    time_limit = models.IntegerField(
        verbose_name=_("time limit (ms)"),
        null=True,
        blank=False,
        validators=[validate_time_limit],
    )
    memory_limit = models.IntegerField(
        verbose_name=_("memory limit (KiB)"),
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

    def __str__(self):
        return str(self.name)

    class Meta(object):
        ordering = ['order']
        verbose_name = _("test")
        verbose_name_plural = _("tests")
        unique_together = ('problem_instance', 'name')


class LanguageOverrideForTest(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    time_limit = models.IntegerField(
        verbose_name=_("time limit (ms)"),
        null=True,
        blank=False,
        validators=[validate_time_limit],
    )
    memory_limit = models.IntegerField(
        verbose_name=_("memory limit (KiB)"),
        null=True,
        blank=True,
        validators=[validate_memory_limit],
    )
    language = models.CharField(max_length=30, verbose_name=_("language"))

    class Meta(object):
        ordering = ['test__order']
        verbose_name = _("test limit override")
        verbose_name_plural = _("tests limit overrides")
        unique_together = ('test', 'language')


class OutputChecker(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    exe_file = FileField(
        upload_to=make_problem_filename,
        null=True,
        blank=True,
        verbose_name=_("checker executable file"),
    )

    class Meta(object):
        verbose_name = _("output checker")
        verbose_name_plural = _("output checkers")


class LibraryProblemData(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    libname = models.CharField(
        max_length=30,
        verbose_name=_("libname"),
        help_text=_("Filename that the library should be given during compilation"),
    )

    class Meta(object):
        verbose_name = _("library problem data")
        verbose_name_plural = _("library problem data")


model_solution_kinds = EnumRegistry()
model_solution_kinds.register('NORMAL', _("Model solution"))
model_solution_kinds.register('SLOW', _("Slow solution"))
model_solution_kinds.register('INCORRECT', _("Incorrect solution"))


class ModelSolutionsManager(models.Manager):
    def recreate_model_submissions(self, problem_instance, model_solution=None):
        with transaction.atomic():
            query = ModelProgramSubmission.objects.filter(
                problem_instance=problem_instance
            )
            if model_solution is not None:
                query = query.filter(model_solution=model_solution)
            query.delete()
        if not problem_instance.round and problem_instance.contest is not None:
            return
        if model_solution is None:
            model_solutions = self.filter(problem=problem_instance.problem)
        else:
            model_solutions = [model_solution]
        for model_solution in model_solutions:
            with transaction.atomic():
                submission = ModelProgramSubmission(
                    model_solution=model_solution,
                    problem_instance=problem_instance,
                    source_file=model_solution.source_file,
                    kind='IGNORED',
                )
                submission.save()
            problem_instance.controller.judge(submission, is_rejudge=True)


class ModelSolution(models.Model):
    objects = ModelSolutionsManager()

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name=_("name"))
    source_file = FileField(upload_to=make_problem_filename, verbose_name=_("source"))
    kind = EnumField(model_solution_kinds, verbose_name=_("kind"))
    order_key = models.IntegerField(default=0)

    @property
    def short_name(self):
        return self.name.rsplit('.', 1)[0]


@receiver(pre_save, sender=ProblemInstance)
def _decide_if_autocreate_model_submissions_for_problem_instance(
    sender, instance, raw, **kwargs
):
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
def _autocreate_model_submissions_for_problem_instance(
    sender, instance, created, raw, **kwargs
):
    if instance.create_model_submissions:
        ModelSolution.objects.recreate_model_submissions(instance)


@receiver(post_save, sender=ModelSolution)
def _autocreate_model_submissions_for_model_solutions(
    sender, instance, created, raw, **kwargs
):
    if created and not raw:
        pis = ProblemInstance.objects.filter(problem=instance.problem)
        for pi in pis:
            ModelSolution.objects.recreate_model_submissions(pi, instance)


def make_submission_filename(instance, filename):
    if not instance.id:
        instance.save()
    if instance.problem_instance.contest is not None:
        folder = instance.problem_instance.contest_id
    else:
        folder = "main_problem_instance"
    return 'submissions/%s/%d%s' % (folder, instance.id, os.path.splitext(filename)[1])


class ProgramSubmission(Submission):
    source_file = FileField(upload_to=make_submission_filename)
    source_length = models.IntegerField(
        verbose_name=_("Source code length"), blank=True, null=True
    )

    def save(self, *args, **kwargs):
        if self.source_file:
            self.source_length = self.source_file.size
        super(ProgramSubmission, self).save(*args, **kwargs)

    @property
    def extension(self):
        return os.path.splitext(self.source_file.name)[1][1:]

    def get_language_display(self):
        return get_language_by_extension(self.problem_instance, self.extension)


class ModelProgramSubmission(ProgramSubmission):
    model_solution = models.ForeignKey(ModelSolution, on_delete=models.CASCADE)


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
submission_report_kinds.register('HIDDEN', _("Hidden report (for admins only)"))
submission_report_kinds.register('USER_OUTS', _("Report with user out"))


class CompilationReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    status = EnumField(submission_statuses)
    compiler_output = models.TextField()


def make_output_filename(instance, filename):
    # This code is dead (it's result is ignored) with current implementation
    # of assigning file from filetracker to a FileField.
    submission = instance.submission_report.submission
    return 'userouts/%s/%d/%d-out' % (
        submission.problem_instance.contest_id,
        submission.id,
        instance.submission_report_id,
    )


class TestReport(models.Model):
    __test__ = False
    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    status = EnumField(submission_statuses)
    comment = models.CharField(max_length=255, blank=True)
    score = ScoreField(null=True, blank=True)
    max_score = ScoreField(null=True, blank=True)
    time_used = models.IntegerField(blank=True)
    output_file = FileField(upload_to=make_output_filename, null=True, blank=True)

    test = models.ForeignKey(Test, blank=True, null=True, on_delete=models.SET_NULL)
    test_name = models.CharField(max_length=30)
    test_group = models.CharField(max_length=30)
    test_time_limit = models.IntegerField(null=True, blank=True)


class GroupReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    group = models.CharField(max_length=30)
    score = ScoreField(null=True, blank=True)
    max_score = ScoreField(null=True, blank=True)
    status = EnumField(submission_statuses)


class ReportActionsConfig(models.Model):
    problem = models.OneToOneField(
        Problem,
        verbose_name=_("problem instance"),
        related_name='report_actions_config',
        primary_key=True,
        on_delete=models.CASCADE,
    )
    can_user_generate_outs = models.BooleanField(
        default=False,
        verbose_name=_(
            "Allow users to generate their outs on tests from visible reports."
        ),
    )


class UserOutGenStatus(models.Model):
    testreport = models.OneToOneField(
        TestReport,
        primary_key=True,
        related_name='userout_status',
        on_delete=models.CASCADE,
    )
    status = EnumField(submission_statuses, default='?')
    visible_for_user = models.BooleanField(default=True)


class ProblemCompiler(models.Model):
    """Represents compiler used for a given language for this problem.
    This can be altered by contest specific compilers."""

    problem = models.ForeignKey(
        Problem, verbose_name=_("problem"), on_delete=models.CASCADE
    )
    language = models.CharField(max_length=20, verbose_name=_("language"))
    compiler = models.CharField(max_length=50, verbose_name=_("compiler"))
    auto_created = models.BooleanField(default=False, editable=False)

    class Meta(object):
        verbose_name = _("problem compiler")
        verbose_name_plural = _("problem compilers")
        ordering = ('problem',)
        unique_together = ('problem', 'language')


@receiver(post_save, sender=Problem)
def _autocreate_problem_compilers_for_problem(
    sender, instance, created, raw, using, **kwargs
):
    # we want to do this only if object is newly created
    if created:
        # create problem compilers for every language and populate with defaults
        for language in getattr(settings, "SUBMITTABLE_LANGUAGES", {}):
            problem_compiler = ProblemCompiler(
                problem=instance,
                language=language,
                compiler=settings.DEFAULT_COMPILERS[language],
                auto_created=True,
            )
            problem_compiler.save()


class ContestCompiler(models.Model):
    """Represents compilers set for languages in different contests.
    This is used to allow overriding problems' compilers inside a contest."""

    contest = models.ForeignKey(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    language = models.CharField(max_length=20, verbose_name=_("language"))
    compiler = models.CharField(max_length=50, verbose_name=_("compiler"))

    class Meta(object):
        verbose_name = _("contest compiler")
        verbose_name_plural = _("contest compilers")
        ordering = ('contest',)
        unique_together = ('contest', 'language')


class ProblemAllowedLanguage(models.Model):
    """Represents allowed language for specific problem."""

    problem = models.ForeignKey(
        Problem, verbose_name=_("problem"), on_delete=models.CASCADE
    )
    language = models.CharField(max_length=20, verbose_name=_("language"))

    class Meta(object):
        verbose_name = _("problem allowed language")
        verbose_name_plural = _("problem allowed languages")
        ordering = ('problem',)
        unique_together = ('problem', 'language')


def check_compilers_config():
    SUBMITTABLE_LANGUAGES = getattr(settings, "SUBMITTABLE_LANGUAGES", {})
    SUBMITTABLE_EXTENSIONS = getattr(settings, "SUBMITTABLE_EXTENSIONS", {})
    AVAILABLE_COMPILERS = getattr(settings, "AVAILABLE_COMPILERS", {})
    DEFAULT_COMPILERS = getattr(settings, "DEFAULT_COMPILERS", {})
    for language, language_info in SUBMITTABLE_LANGUAGES.items():
        if not language_info.get('display_name'):
            raise ImproperlyConfigured
        if language_info.get('type', 'main') not in ['main', 'extra']:
            raise ImproperlyConfigured
        if not SUBMITTABLE_EXTENSIONS.get(language):
            raise ImproperlyConfigured
        compilers_for_lang = AVAILABLE_COMPILERS.get(language)
        if not compilers_for_lang:
            raise ImproperlyConfigured
        else:
            for compiler, compiler_info in compilers_for_lang.items():
                if 'display_name' not in compiler_info:
                    raise ImproperlyConfigured
        if not DEFAULT_COMPILERS.get(language):
            raise ImproperlyConfigured
        if DEFAULT_COMPILERS[language] not in AVAILABLE_COMPILERS[language]:
            raise ImproperlyConfigured


check_compilers_config()
