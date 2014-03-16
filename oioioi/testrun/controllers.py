from django.template.loader import render_to_string
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.context import RequestContext
from django.contrib.auth.models import User

from oioioi.programs.controllers import ProgrammingContestController, \
    ProgrammingProblemController
from oioioi.testrun.models import TestRunProgramSubmission, TestRunReport
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
                validators=[validate_file_size], label=_("Input"),
                help_text=_("Keep in mind that this feature does not provide"
                            " any validation of your input or output."))

        if 'kind' in form.fields:
            form.fields['kind'].choices = [('TESTRUN', _("Test run")), ]

    def create_testrun(self, request, problem_instance, form_data,
            commit=True, model=TestRunProgramSubmission):
        submission = model(
                user=form_data.get('user', request.user),
                problem_instance=problem_instance,
                kind='TESTRUN')
        submit_file = form_data['file']
        if submit_file is None:
            lang_exts = getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})
            extension = lang_exts[form_data['prog_lang']][0]
            submit_file = ContentFile(form_data['code'],
                    '__pasted_code.' + extension)
        submission.source_file.save(submit_file.name, submit_file)
        input_file = form_data['input']
        submission.input_file.save(input_file.name, input_file)
        if commit:
            submission.save()
            self.judge(submission)
        return submission

    def update_submission_score(self, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .update_submission_score(submission)

        try:
            report = SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind='TESTRUN').get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.status = score_report.status
            submission.score = score_report.score  # Should be None
        except ObjectDoesNotExist:
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

    def get_supported_extra_args(self, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .get_supported_extra_args(submission)
        return {}

    def render_submission(self, request, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                    .render_submission(request, submission)

        return render_to_string('testrun/submission_header.html',
            context_instance=RequestContext(request,
                {'submission': submission_template_context(request,
                    submission.programsubmission.testrunprogramsubmission),
                'supported_extra_args':
                    self.get_supported_extra_args(submission)}))

    def _render_testrun_report(self, request, report, testrun_report,
            template='testrun/report.html'):
        score_report = ScoreReport.objects.get(submission_report=report)
        compilation_report = \
            CompilationReport.objects.get(submission_report=report)
        output_container_id_prefix = \
            request.is_ajax() and 'hidden_output_data_' or 'output_data_'

        return render_to_string(template,
            context_instance=RequestContext(request, {
                'report': report, 'score_report': score_report,
                'compilation_report': compilation_report,
                'testrun_report': testrun_report,
                'output_container_id_prefix': output_container_id_prefix}))

    def render_report(self, request, report, *args, **kwargs):
        if report.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self) \
                .render_report(request, report, *args, **kwargs)

        # It may not exists when compilation error occurs
        try:
            testrun_report = TestRunReport.objects.get(
                    submission_report=report)
        except TestRunReport.DoesNotExist:
            testrun_report = None

        return self._render_testrun_report(request, report, testrun_report)

    def valid_kinds_for_submission(self, submission):
        if submission.kind != 'TESTRUN':
            return super(TestRunContestControllerMixin, self). \
                valid_kinds_for_submission(submission)

        assert submission.kind == 'TESTRUN'
        return ['TESTRUN']

    def users_to_receive_public_message_notification(self):
        return self.registration_controller().filter_participants(User
                .objects.all())

ProgrammingContestController.mix_in(TestRunContestControllerMixin)
