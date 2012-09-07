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
from oioioi.problems.admin import ProblemAdmin
from oioioi.programs.models import Test, ModelSolution, TestReport, \
        GroupReport, ModelProgramSubmission
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
    ordering = ('kind', 'name')

    class Media:
        css = {
            'all': ('programs/admin.css',),
        }

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

class ProgrammingProblemAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ProgrammingProblemAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [TestInline]

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

        test_reports = TestReport.objects \
                .filter(submission_report__submission__problem_instance=problem_instance) \
                .filter(submission_report__submission__programsubmission__modelprogramsubmission__isnull=False) \
                .filter(test__isnull=False) \
                .select_related()
        group_reports = GroupReport.objects \
                .filter(submission_report__submission__problem_instance=problem_instance) \
                .filter(submission_report__submission__programsubmission__modelprogramsubmission__isnull=False) \
                .select_related()
        submissions = ModelProgramSubmission.objects \
                .filter(problem_instance=problem_instance) \
                .order_by('model_solution__name') \
                .select_related('model_solution') \
                .all()
        tests = problem_instance.problem.test_set \
                .order_by('group', 'name').all()

        group_results = defaultdict(lambda: defaultdict(lambda: None))
        for gr in group_reports:
            group_results[gr.group][gr.submission_report.submission_id] = gr

        test_results = defaultdict(lambda: defaultdict(lambda: None))
        for tr in test_reports:
            test_results[tr.test_id][tr.submission_report.submission_id] = tr

        rows = []
        for t in tests:
            row_test_results = test_results[t.id]
            row_group_results = group_results[t.group]
            rows.append({
                'test': t,
                'results': [{
                        'test_report': row_test_results[s.id],
                        'group_report': row_group_results[s.id],
                        'is_partial_score': self._is_partial_score(
                            row_test_results[s.id])
                    } for s in submissions]
                })

        context = {
                'problem_instance': problem_instance,
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
                url(r'(\d+)/models/rejudge$',
                    self.rejudge_model_solutions_view,
                    name='contests_probleminstance_models_rejudge'),
            )
        return extra_urls + urls

    def inline_actions(self, instance):
        actions = super(ProgrammingProblemInstanceAdminMixin,
                self).inline_actions(instance)
        if ModelSolution.objects.filter(problem_id=instance.problem_id):
            models_view = reverse('oioioiadmin:contests_probleminstance_models',
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
    user_full_name.short_description = SubmissionAdmin.user_full_name.short_description
    user_full_name.admin_order_field = SubmissionAdmin.user_full_name.admin_order_field

SubmissionAdmin.mix_in(ModelSubmissionAdminMixin)
