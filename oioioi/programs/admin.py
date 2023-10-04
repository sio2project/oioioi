from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.models import BaseInlineFormSet
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import conditional_escape
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import make_html_link
from oioioi.contests.admin import ContestAdmin, ProblemInstanceAdmin, SubmissionAdmin
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import is_contest_admin
from oioioi.programs.utils import get_submittable_languages
from oioioi.problems.admin import MainProblemInstanceAdmin, ProblemPackageAdmin
from oioioi.programs.forms import (
    CompilerInlineForm,
    ProblemAllowedLanguageInlineForm,
    ProblemCompilerInlineForm,
)
from oioioi.programs.models import (
    ContestCompiler,
    LibraryProblemData,
    ModelSolution,
    OutputChecker,
    ProblemAllowedLanguage,
    ProblemCompiler,
    ProgramsConfig,
    ReportActionsConfig,
    Test,
)


class ProgramsConfigInline(admin.TabularInline):
    model = ProgramsConfig
    can_delete = False
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class ValidationFormset(BaseInlineFormSet):
    def get_time_limit_sum(self):
        time_limit_sum = 0
        for test in self.cleaned_data:
            time_limit_sum += test['time_limit']
        return time_limit_sum

    def validate_max_scores_in_group(self):
        score_in_group = dict()
        for test_data in self.cleaned_data:
            test = test_data['id']
            if (
                test.group in list(score_in_group.keys())
                and score_in_group[test.group] != test_data['max_score']
            ):
                raise ValidationError(
                    "Scores for tests in the same group must be equal"
                )
            elif test.group not in list(score_in_group.keys()):
                score_in_group[test.group] = test_data['max_score']

    def validate_time_limit_sum(self):
        time_limit_per_problem = settings.MAX_TEST_TIME_LIMIT_PER_PROBLEM

        if self.get_time_limit_sum() > time_limit_per_problem:
            time_limit_sum_rounded = (self.get_time_limit_sum() + 999) / 1000.0
            limit_seconds = time_limit_per_problem / 1000.0

            raise ValidationError(
                _(
                    "Sum of time limits for all tests is too big. It's %(sum)ds, "
                    "but it shouldn't exceed %(limit)ds."
                )
                % {'sum': time_limit_sum_rounded, 'limit': limit_seconds}
            )

    def clean(self):
        try:
            self.validate_time_limit_sum()
            self.validate_max_scores_in_group()
            return self.cleaned_data
        except AttributeError:
            pass


class TestInline(admin.TabularInline):
    model = Test
    max_num = 0
    extra = 0
    template = 'programs/admin/tests_inline.html'
    can_delete = False
    fields = (
        'name',
        'time_limit',
        'memory_limit',
        'max_score',
        'kind',
        'input_file_link',
        'output_file_link',
        'is_active',
    )
    readonly_fields = ('name', 'kind', 'group', 'input_file_link', 'output_file_link')
    ordering = ('kind', 'order', 'name')
    formset = ValidationFormset

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # this view doesn't allow to add / remove tests
        # so if there are no tests for this tasks we can skip showing it
        # (for example quizzes have no tests and it would be confusing to show)
        return obj is None or obj.test_set.count() != 0

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def input_file_link(self, instance):
        if instance.id is not None:
            href = reverse('download_input_file', kwargs={'test_id': str(instance.id)})
            return make_html_link(href, instance.input_file.name.split('/')[-1])
        return None

    input_file_link.short_description = _("Input file")

    def output_file_link(self, instance):
        if instance.id is not None:
            href = reverse('download_output_file', kwargs={'test_id': instance.id})
            return make_html_link(href, instance.output_file.name.split('/')[-1])
        return None

    output_file_link.short_description = _("Output/hint file")


class ReportActionsConfigInline(admin.StackedInline):
    model = ReportActionsConfig
    extra = 0
    inline_classes = ('collapse open',)
    fields = ['can_user_generate_outs']
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class OutputCheckerInline(admin.TabularInline):
    model = OutputChecker
    extra = 0
    fields = ['checker_link']
    readonly_fields = ['checker_link']
    can_delete = False
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def checker_link(self, instance):
        if not instance.exe_file:
            return _("No checker for this task.")

        if instance.id is not None:
            href = reverse(
                'download_checker_file', kwargs={'checker_id': str(instance.id)}
            )
            return make_html_link(href, instance.exe_file.name.split('/')[-1])
        return None

    checker_link.short_description = _("Checker exe")


class LibraryProblemDataInline(admin.TabularInline):
    model = LibraryProblemData
    extra = 0
    fields = ['libname']
    readonly_fields = ['libname']
    can_delete = False
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class ProblemCompilerInline(admin.StackedInline):
    model = ProblemCompiler
    extra = 0
    form = ProblemCompilerInlineForm
    category = _("Advanced")


class ProblemAllowedLanguageInline(admin.StackedInline):
    model = ProblemAllowedLanguage
    extra = 0
    form = ProblemAllowedLanguageInlineForm
    category = _("Advanced")


class ContestCompilerInline(admin.StackedInline):
    model = ContestCompiler
    extra = 0
    form = CompilerInlineForm
    category = _("Advanced")

    def __init__(self, *args, **kwargs):
        super(ContestCompilerInline, self).__init__(*args, **kwargs)
        self.verbose_name_plural = _("Compiler overrides")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class ProgramsContestAdminMixin(object):
    """Adds :class:`~oioioi.programs.models.ProgramsConfig`
    and :class:`~oioioi.programs.models.ContestCompiler` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(ProgramsContestAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ProgramsConfigInline, ContestCompilerInline)


ContestAdmin.mix_in(ProgramsContestAdminMixin)


class LibraryProblemDataAdminMixin(object):
    """Adds :class:`~oioioi.programs.models.LibraryProblemData` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(LibraryProblemDataAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (LibraryProblemDataInline,)


class ProgrammingProblemAdminMixin(object):
    """Adds :class:`~oioioi.programs.models.ReportActionsConfig`,
    :class:`~oioioi.programs.models.OutputChecker`,
    :class:`~oioioi.programs.models.LibraryProblemData` and
    :class:`~oioioi.programs.models.ProblemAllowedLanguage` and
    :class:`~oioioi.programs.models.ProblemCompiler` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(ProgrammingProblemAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (
            ReportActionsConfigInline,
            OutputCheckerInline,
            LibraryProblemDataInline,
            ProblemCompilerInline,
            ProblemAllowedLanguageInline,
        )


class ProgrammingProblemInstanceAdminMixin(object):
    """Adds :class:`~oioioi.programs.models.Test` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(ProgrammingProblemInstanceAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (TestInline,)


ProblemInstanceAdmin.mix_in(ProgrammingProblemInstanceAdminMixin)


class ProgrammingMainProblemInstanceAdminMixin(object):
    """Adds :class:`~oioioi.programs.models.Test` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(ProgrammingMainProblemInstanceAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (TestInline,)


MainProblemInstanceAdmin.mix_in(ProgrammingMainProblemInstanceAdminMixin)


class ProblemPackageAdminMixin(object):
    """Adds model solutions action to an admin panel."""

    def inline_actions(self, package_instance, contest):
        actions = super(ProblemPackageAdminMixin, self).inline_actions(
            package_instance, contest
        )
        if package_instance.status == 'OK':
            try:
                problem_instance = package_instance.problem.main_problem_instance
                if not problem_instance:
                    problem_instance = ProblemInstance.objects.get(
                        problem=package_instance.problem, contest=contest
                    )
                if problem_instance.contest and ModelSolution.objects.filter(
                    problem=problem_instance.problem
                ):
                    models_view = reverse(
                        'model_solutions', args=(problem_instance.id,)
                    )
                    actions.append((models_view, _("Model solutions")))
            except ProblemInstance.DoesNotExist:
                pass
        return actions


ProblemPackageAdmin.mix_in(ProblemPackageAdminMixin)


class ModelSubmissionAdminMixin(object):
    """Adds model submission to an admin panel."""

    def user_full_name(self, instance):
        if not instance.user:
            instance = instance.programsubmission
            if instance:
                instance = instance.modelprogramsubmission
                if instance:
                    return '(%s)' % (
                        conditional_escape(force_str(instance.model_solution.name)),
                    )
        return super(ModelSubmissionAdminMixin, self).user_full_name(instance)

    user_full_name.short_description = SubmissionAdmin.user_full_name.short_description
    user_full_name.admin_order_field = SubmissionAdmin.user_full_name.admin_order_field

    def get_custom_list_select_related(self):
        return super(
            ModelSubmissionAdminMixin, self
        ).get_custom_list_select_related() + [
            'programsubmission',
            'programsubmission__modelprogramsubmission',
        ]


SubmissionAdmin.mix_in(ModelSubmissionAdminMixin)


class ProgramSubmissionAdminMixin(object):
    """Adds submission diff action, language display and language filter to
    an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(ProgramSubmissionAdminMixin, self).__init__(*args, **kwargs)
        self.actions += ['submission_diff_action']

    def get_list_display(self, request):
        return super(ProgramSubmissionAdminMixin, self).get_list_display(request) + [
            'language_display'
        ]

    def get_list_filter(self, request):
        return super(ProgramSubmissionAdminMixin, self).get_list_filter(request) + [
            LanguageListFilter
        ]

    def language_display(self, instance):
        return instance.programsubmission.get_language_display()

    language_display.short_description = _("Language")

    def submission_diff_action(self, request, queryset):
        if len(queryset) != 2:
            messages.error(
                request, _("You shall select exactly two submissions to diff")
            )
            return None

        id_older, id_newer = [sub.id for sub in queryset.order_by('date')]

        return redirect(
            'source_diff',
            contest_id=request.contest.id,
            submission1_id=id_older,
            submission2_id=id_newer,
        )

    submission_diff_action.short_description = _("Diff submissions")


SubmissionAdmin.mix_in(ProgramSubmissionAdminMixin)


class LanguageListFilter(SimpleListFilter):
    title = _("language")
    parameter_name = 'lang'

    def lookups(self, request, model_admin):
        langs = get_submittable_languages()
        return [(lang, lang_info['display_name']) for lang, lang_info in langs.items()]

    def queryset(self, request, queryset):
        exts = getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})
        if self.value() and self.value() in exts:
            condition = Q()
            for ext in exts[self.value()]:
                condition |= Q(programsubmission__source_file__contains='.%s@' % ext)
            return queryset.filter(condition)
        else:
            return queryset
