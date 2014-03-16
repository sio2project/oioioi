from django import forms
from django.core.exceptions import ValidationError
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.controllers import submission_template_context

from oioioi.evalmgr import recipe_placeholder
from oioioi.problems.controllers import ProblemController
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.zeus.admin import ZeusProblemAdminMixin
from oioioi.zeus.models import ZeusProblemData, ZeusTestRunProgramSubmission, ZeusTestRunReport
from oioioi.zeus.utils import has_any_zeus_testrun_problem, is_zeus_problem


class ZeusProblemController(ProblemController):
    description = _("Zeus programming problem")

    def generate_base_environ(self, environ, **kwargs):
        zeus_problem = ZeusProblemData.objects.get(problem=self.problem)
        environ['recipe'] = []
        environ['zeus_id'] = zeus_problem.zeus_id
        environ['zeus_problem_id'] = zeus_problem.zeus_problem_id

    def generate_recipe(self, kinds):
        recipe_body = [
        ]

        if 'INITIAL' in kinds:
            recipe_body.extend(
                [
                    recipe_placeholder('before_initial_tests'),
                    ('initial_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='INITIAL')),
                    recipe_placeholder('before_initial_async'),
                    ('initial_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='INITIAL')),

                    # current job ends here, the following will be asynchronous
                    ('initial_import_tests',
                        'oioioi.zeus.handlers.import_results',
                        dict(kind='INITIAL', map_to_kind='EXAMPLE')),
                    ('initial_grade_tests',
                        'oioioi.programs.handlers.grade_tests'),
                    ('initial_grade_groups',
                        'oioioi.programs.handlers.grade_groups'),
                    ('initial_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind='EXAMPLE')),
                    ('initial_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='INITIAL')),
                    recipe_placeholder('after_initial_tests'),
                ]
            )

        if 'NORMAL' in kinds:
            recipe_body.extend(
                [
                    recipe_placeholder('before_final_tests'),
                    ('final_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='NORMAL')),
                    recipe_placeholder('before_final_async'),
                    ('final_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='NORMAL')),

                    # current job ends here, the following will be asynchronous
                    ('final_import_results',
                        'oioioi.zeus.handlers.import_results',
                        dict(kind='NORMAL')),
                    ('final_grade_tests',
                        'oioioi.programs.handlers.grade_tests'),
                    ('final_grade_groups',
                        'oioioi.programs.handlers.grade_groups'),
                    ('final_grade_submission',
                        'oioioi.programs.handlers.grade_submission'),
                    ('final_make_report',
                        'oioioi.programs.handlers.make_report'),
                    recipe_placeholder('after_final_tests'),
                ])

        if 'HIDDEN' in kinds:
            recipe_body.extend(
                [
                    ('initial_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='INITIAL')),
                    recipe_placeholder('before_initial_async'),
                    ('initial_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='INITIAL')),

                    # current job ends here, the following will be asynchronous
                    ('final_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='NORMAL')),
                    recipe_placeholder('before_final_async'),
                    ('final_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='NORMAL')),

                    # another asynchronous part
                    ('initial_import_tests',
                        'oioioi.zeus.handlers.import_results',
                        dict(kind='INITIAL', map_to_kind='EXAMPLE')),
                    ('normal_import_tests',
                        'oioioi.zeus.handlers.import_results',
                        dict(kind='NORMAL')),
                    ('hidden_grade_tests',
                        'oioioi.programs.handlers.grade_tests'),
                    ('hidden_grade_groups',
                        'oioioi.programs.handlers.grade_groups'),
                    ('hidden_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None)),
                    ('hidden_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='HIDDEN')),
                    recipe_placeholder('after_all_tests'),
                ])

        return recipe_body

    def fill_evaluation_environ(self, environ, **kwargs):
        self.generate_base_environ(environ, **kwargs)

        environ['recipe'].extend(self.generate_recipe(environ['report_kinds']))

        environ.setdefault('group_scorer',
            'oioioi.programs.utils.min_group_scorer')
        environ.setdefault('score_aggregator',
            'oioioi.programs.utils.sum_score_aggregator')

    def mixins_for_admin(self):
        return super(ZeusProblemController, self).mixins_for_admin() + \
                (ZeusProblemAdminMixin,)


class ZeusTestRunProblemControllerMixin(object):
    def fill_evaluation_environ(self, environ, **kwargs):
        if environ['submission_kind'] != 'TESTRUN':
            return super(ZeusTestRunProblemControllerMixin, self) \
                .fill_evaluation_environ(environ, **kwargs)

        self.generate_base_environ(environ, **kwargs)
        recipe_body = [
            ('submit_testrun_job',
                'oioioi.zeus.handlers.submit_testrun_job'),
            recipe_placeholder('before_testrun_async'),
            ('save_async_job',
                'oioioi.zeus.handlers.save_env',
                dict(kind='TESTRUN')),

            # current job ends here, the following will be asynchronous
            ('import_results',
                'oioioi.zeus.handlers.import_results',
                dict(kind='TESTRUN')),
            ('grade_submission',
                'oioioi.testrun.handlers.grade_submission'),
            ('make_report',
                'oioioi.zeus.handlers.make_zeus_testrun_report'),
        ]
        environ['recipe'].extend(recipe_body)
        environ['zeus_metadata_decoder'] = \
                'oioioi.zeus.handlers.testrun_metadata'

    def mixins_for_admin(self):
        from oioioi.testrun.admin import TestRunProgrammingProblemAdminMixin
        return super(ZeusTestRunProblemControllerMixin, self) \
                   .mixins_for_admin() + (TestRunProgrammingProblemAdminMixin,)

ZeusProblemController.mix_in(ZeusTestRunProblemControllerMixin)


class ZeusContestControllerMixin(object):
    def get_testrun_library_limit(self):
        return 100 * 1000  # in bytes

    def adjust_submission_form(self, request, form):
        super(ZeusContestControllerMixin, self) \
                .adjust_submission_form(request, form)

        if form.kind != 'TESTRUN' or not has_any_zeus_testrun_problem(request):
            return

        def validate_library_file_size(file):
            if file.size > self.get_testrun_library_limit():
                raise ValidationError(_("Library file size limit exceeded."))

        form.fields['library'] = forms.FileField(allow_empty_file=True,
                validators=[validate_library_file_size], label=_("Library"),
                help_text=_("Your solution will be compiled with this file "
                            "as the library header."
                            "You can implement required functions here."))

    def create_testrun(self, request, problem_instance, form_data,
            commit=True):
        if not is_zeus_problem(problem_instance.problem):
            return super(ZeusContestControllerMixin, self).create_testrun(
                    request, problem_instance, form_data, commit)

        submission = super(ZeusContestControllerMixin, self).create_testrun(
                request, problem_instance, form_data, commit=False,
                model=ZeusTestRunProgramSubmission)

        # TODO: if is task with library
        if 'library' in form_data:
            library_file = form_data['library']
            submission.library_file.save(library_file.name, library_file)

        if commit:
            submission.save()
            self.judge(submission)
        return submission

    def render_submission(self, request, submission):
        if submission.kind != 'TESTRUN' or \
                not is_zeus_problem(submission.problem_instance.problem):
            return super(ZeusContestControllerMixin, self) \
                    .render_submission(request, submission)

        if not isinstance(submission, ZeusTestRunProgramSubmission):
            submission = ZeusTestRunProgramSubmission.objects \
                    .get(id=submission.id)
        return render_to_string('zeus/submission_header.html',
            context_instance=RequestContext(request,
                {'submission': submission_template_context(request,
                    submission),
                'supported_extra_args':
                    self.get_supported_extra_args(submission)}))

    def _render_testrun_report(self, request, report, testrun_report,
            template='testrun/report.html'):
        try:
            testrun_report = testrun_report.zeustestrunreport
            template = 'zeus/report.html'
        except ZeusTestRunReport.DoesNotExist:
            pass
        return super(ZeusContestControllerMixin, self)._render_testrun_report(
                request, report, testrun_report, template)

ProgrammingContestController.mix_in(ZeusContestControllerMixin)
