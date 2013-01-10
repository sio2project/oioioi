from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from oioioi.programs.controllers import ProgrammingContestController, \
    ProgrammingProblemController
from oioioi.testrun.models import TestRunProgramSubmission, TestRunReport, \
    TestRunConfig
from django.template.context import RequestContext
from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import SubmissionReport, ScoreReport
from oioioi.evalmgr import extend_after_placeholder
from oioioi.programs.models import CompilationReport


class TestRunProblemControllerMixin(object):
    def fill_evaluation_environ(self, environ, **kwargs):
        if environ['submission_kind'] != 'TESTRUN':
            return super(TestRunProblemControllerMixin, self) \
                .fill_evaluation_environ(environ, **kwargs)

        self.generate_base_environ(environ, **kwargs)
        recipe_body = [
                ('make_test',
                    'oioioi.testrun.handlers.make_test'),
                ('run_tests',
                    'oioioi.programs.handlers.run_tests',),
                ('grade_submission',
                    'oioioi.testrun.handlers.grade_submission'),
                ('make_report',
                    'oioioi.testrun.handlers.make_report'),
            ]
        extend_after_placeholder(environ, 'after_compile', recipe_body)

        environ['error_handlers'].append(('delete_output',
                'oioioi.testrun.handlers.delete_output'))

        environ['save_outputs'] = True
        environ['check_outputs'] = False

    def mixins_for_admin(self):
        from oioioi.testrun.admin import TestRunProgrammingProblemAdminMixin
        return super(TestRunProblemControllerMixin, self) \
                .mixins_for_admin() + (TestRunProgrammingProblemAdminMixin,)

ProgrammingProblemController.mix_in(TestRunProblemControllerMixin)

class TestRunContestControllerMixin(object):
    def fill_evaluation_environ_post_problem(self, environ, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                    .fill_evaluation_environ_post_problem(environ, submission)

    def get_testrun_input_limit(self):
        return getattr(settings, 'TESTRUN_INPUT_LIMIT', 100 * 1024)

    def adjust_submission_form(self, request, form):
        super(TestRunContestControllerMixin, self) \
            .adjust_submission_form(request, form)

        if form.kind != 'TESTRUN':
            return

        def validate_file_size(file):
            if file.size > self.get_testrun_input_limit():
                raise ValidationError(_("Input file size limit exceeded."))

        form.fields['input'] = forms.FileField(allow_empty_file=True,
                validators=[validate_file_size], label=_("Input"))

        if 'kind' in form.fields:
            form.fields['kind'].choices = [('TESTRUN', _("Test run")), ]

    def create_testrun(self, request, problem_instance, form_data):
        submission = TestRunProgramSubmission(
                user=form_data.get('user', request.user),
                problem_instance=problem_instance,
                kind='TESTRUN')
        submit_file = form_data['file']
        submission.source_file.save(submit_file.name, submit_file)
        input_file = form_data['input']
        submission.input_file.save(input_file.name, input_file)
        submission.save()
        self.judge(submission)

    def update_submission_score(self, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .update_submission_score(submission)

        try:
            report = SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind='TESTRUN').get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.status = score_report.status
            submission.score = score_report.score  #Should be None
        except:
            if SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind='FAILURE'):
                submission.status = 'SE'
            else:
                submission.status = '?'
        submission.save()

    def update_report_statuses(self, submission, queryset):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .update_report_statuses(submission, queryset)

        self._activate_newest_report(submission, queryset,
                kind=['TESTRUN', 'FAILURE'])

    def can_see_submission_status(self, request, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .can_see_submission_status(request, submission)

        return True

    def get_visible_reports_kinds(self, request, submission):
        return ['TESTRUN'] + super(TestRunContestControllerMixin, self) \
                .get_visible_reports_kinds(request, submission)

    def render_submission(self, request, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                    .render_submission(request, submission)

        return render_to_string('testrun/submission_header.html',
            context_instance=RequestContext(request, {'submission':
                submission_template_context(request,
                    submission.programsubmission.testrunprogramsubmission)}))

    def render_report(self, request, report):
        if report.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .render_report(request, report)

        score_report = ScoreReport.objects.get(submission_report=report)
        compilation_report = \
                CompilationReport.objects.get(submission_report=report)
        # It may not exists when compilation error occurs
        try:
            testrun_report = TestRunReport.objects.get(submission_report=report)
        except:
            testrun_report = None

        return render_to_string('testrun/report.html',
                context_instance=RequestContext(request, {
                    'report': report, 'score_report': score_report,
                    'compilation_report': compilation_report,
                    'testrun_report': testrun_report}))

ProgrammingContestController.mix_in(TestRunContestControllerMixin)
