from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.conf.urls import patterns, url
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.admin.util import unquote
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import ProblemInstanceAdmin, SubmissionAdmin
from oioioi.contests.scores import IntegerScore
from oioioi.programs.models import Test, ModelSolution, TestReport, \
        GroupReport, ModelProgramSubmission, OutputChecker
from collections import defaultdict


class TestInline(admin.TabularInline):
    model = Test
    max_num = 0
    extra = 0
    template = 'programs/admin/tests_inline.html'
    can_delete = False
    fields = ('name', 'time_limit', 'memory_limit', 'max_score', 'kind',
            'input_file_link', 'output_file_link')
    readonly_fields = ('name', 'kind', 'group', 'input_file_link',
            'output_file_link')
    ordering = ('kind', 'order', 'name')

    class Media(object):
        css = {
            'all': ('programs/admin.css',),
        }

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def input_file_link(self, instance):
        href = reverse('oioioi.programs.views.download_input_file_view',
                kwargs={'test_id': str(instance.id)})
        return make_html_link(href, instance.input_file.name.split('/')[-1])
    input_file_link.short_description = _("Input file")

    def output_file_link(self, instance):
        href = reverse('oioioi.programs.views.download_output_file_view',
                kwargs={'test_id': instance.id})
        return make_html_link(href, instance.output_file.name.split('/')[-1])
    output_file_link.short_description = _("Output/hint file")


class OutputCheckerInline(admin.TabularInline):
    model = OutputChecker
    extra = 0
    fields = ['checker_link']
    readonly_fields = ['checker_link']
    can_delete = False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def checker_link(self, instance):
        if not instance.exe_file:
            return _("No checker for this task.")

        href = reverse('oioioi.programs.views.download_checker_exe_view',
            kwargs={'checker_id': str(instance.id)})
        return make_html_link(href, instance.exe_file.name.split('/')[-1])
    checker_link.short_description = _("Checker exe")


class ProgrammingProblemAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ProgrammingProblemAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [TestInline, OutputCheckerInline]


class ProgrammingProblemInstanceAdminMixin(object):
    def _is_partial_score(self, test_report):
        if not test_report:
            return False
        if isinstance(test_report.score, IntegerScore):
            return test_report.score.value != test_report.test_max_score
        return False

    def model_solutions_view(self, request, problem_instance_id):
        problem_instance = self.get_object(request,
                unquote(problem_instance_id))
        contest = problem_instance.contest
        if not request.user.has_perm('contests.contest_admin', contest):
            raise PermissionDenied

        filter_kwargs = {
            'test__isnull': False,
            'submission_report__submission__problem_instance':
                problem_instance,
            'submission_report__submission__programsubmission'
                    '__modelprogramsubmission__isnull': False
        }
        test_reports = TestReport.objects.filter(**filter_kwargs) \
                .select_related()
        filter_kwargs = {
            'submission_report__submission__problem_instance':
                problem_instance,
            'submission_report__submission__programsubmission'
                    '__modelprogramsubmission__isnull': False
        }
        group_reports = GroupReport.objects.filter(**filter_kwargs) \
                .select_related()
        submissions = ModelProgramSubmission.objects \
                .filter(problem_instance=problem_instance) \
                .order_by('model_solution__order_key') \
                .select_related('model_solution') \
                .all()
        tests = problem_instance.problem.test_set \
                .order_by('order', 'group', 'name').all()

        group_results = defaultdict(lambda: defaultdict(lambda: None))
        for gr in group_reports:
            group_results[gr.group][gr.submission_report.submission_id] = gr

        test_results = defaultdict(lambda: defaultdict(lambda: None))
        for tr in test_reports:
            test_results[tr.test_id][tr.submission_report.submission_id] = tr

        submissions_percentage_statuses = {s.id: '25' for s in submissions}
        rows = []
        submissions_row = []
        for t in tests:
            row_test_results = test_results[t.id]
            row_group_results = group_results[t.group]
            percentage_statuses = {s.id: '100' for s in submissions}
            for s in submissions:
                if row_test_results[s.id] is not None:
                    time_ratio = float(row_test_results[s.id].time_used) / \
                            row_test_results[s.id].test_time_limit
                    if time_ratio <= 0.25:
                        percentage_statuses[s.id] = '25'
                    elif time_ratio <= 0.50:
                        percentage_statuses[s.id] = '50'
                        if submissions_percentage_statuses[s.id] is not '100':
                            submissions_percentage_statuses[s.id] = '50'
                    else:
                        percentage_statuses[s.id] = '100'
                        submissions_percentage_statuses[s.id] = '100'

            rows.append({
                'test': t,
                'results': [{
                    'test_report': row_test_results[s.id],
                    'group_report': row_group_results[s.id],
                    'is_partial_score': self._is_partial_score(
                        row_test_results[s.id]),
                    'percentage_status': percentage_statuses[s.id]
                } for s in submissions]
            })

        for s in submissions:
            status = s.status
            if s.status == 'OK' or s.status == 'INI_OK':
                status = 'OK' + submissions_percentage_statuses[s.id]

            submissions_row.append({
                'submission': s,
                'status': status
                })

        context = {
                'problem_instance': problem_instance,
                'submissions_row': submissions_row,
                'submissions': submissions,
                'rows': rows
        }

        return TemplateResponse(request, 'programs/admin/model_solutions.html',
                context)

    def rejudge_model_solutions_view(self, request, problem_instance_id):
        problem_instance = self.get_object(request,
                unquote(problem_instance_id))
        contest = problem_instance.contest
        if not request.user.has_perm('contests.contest_admin', contest):
            raise PermissionDenied
        ModelSolution.objects.recreate_model_submissions(problem_instance)
        messages.info(request, _("Model solutions sent for evaluation."))
        return redirect('oioioiadmin:contests_probleminstance_models',
            problem_instance.id)

    def get_urls(self):
        urls = super(ProgrammingProblemInstanceAdminMixin, self).get_urls()
        extra_urls = patterns('',
                url(r'(\d+)/models/$', self.model_solutions_view,
                    name='contests_probleminstance_models'),
                url(r'(\d+)/models/rejudge/$',
                    self.rejudge_model_solutions_view,
                    name='contests_probleminstance_models_rejudge'),
            )
        return extra_urls + urls

    def inline_actions(self, instance):
        actions = super(ProgrammingProblemInstanceAdminMixin, self) \
                .inline_actions(instance)
        if ModelSolution.objects.filter(problem_id=instance.problem_id):
            models_view = reverse(
                    'oioioiadmin:contests_probleminstance_models',
                    args=(instance.id,))
            actions.append((models_view, _("Model solutions")))
        return actions

ProblemInstanceAdmin.mix_in(ProgrammingProblemInstanceAdminMixin)


class ModelSubmissionAdminMixin(object):
    def user_full_name(self, instance):
        if not instance.user:
            instance = instance.programsubmission
            if instance:
                instance = instance.modelprogramsubmission
                if instance:
                    return '(%s)' % (conditional_escape(force_unicode(
                        instance.model_solution.name)),)
        return super(ModelSubmissionAdminMixin, self).user_full_name(instance)

    user_full_name.short_description = \
            SubmissionAdmin.user_full_name.short_description
    user_full_name.admin_order_field = \
            SubmissionAdmin.user_full_name.admin_order_field

    def get_list_select_related(self):
        return super(ModelSubmissionAdminMixin, self) \
                .get_list_select_related() \
                + ['programsubmission', 'modelprogramsubmission']

SubmissionAdmin.mix_in(ModelSubmissionAdminMixin)


class ProgramSubmissionAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ProgramSubmissionAdminMixin, self).__init__(*args, **kwargs)
        self.actions += ['submission_diff_action']

    def submission_diff_action(self, request, queryset):
        if len(queryset) != 2:
            messages.error(request,
                    _("You shall select exactly two submissions to diff"))
            return None

        id_older, id_newer = [sub.id for sub in queryset.order_by('date')]

        return redirect('source_diff', contest_id=request.contest.id,
                        submission1_id=id_older, submission2_id=id_newer)
    submission_diff_action.short_description = _("Diff submissions")

SubmissionAdmin.mix_in(ProgramSubmissionAdminMixin)
