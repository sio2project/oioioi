import os.path
import itertools
import logging
import hashlib
from operator import attrgetter

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django import forms
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from oioioi.base.utils.user_selection import UserSelectionField
from oioioi.contests.utils import is_contest_admin, is_contest_observer
from oioioi.problems.controllers import ProblemController
from oioioi.problems.utils import is_problem_author, \
        can_see_submission_without_contest
from oioioi.contests.controllers import ContestController, \
        submission_template_context
from oioioi.contests.models import SubmissionReport, ScoreReport
from oioioi.programs.models import ProgramSubmission, OutputChecker, \
        CompilationReport, TestReport, GroupReport, ModelProgramSubmission, \
        Submission, UserOutGenStatus
from oioioi.programs.utils import has_report_actions_config
from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.evalmgr import recipe_placeholder, add_before_placeholder, \
        extend_after_placeholder

logger = logging.getLogger(__name__)


class ProgrammingProblemController(ProblemController):
    description = _("Simple programming problem")

    def generate_initial_evaluation_environ(self, environ, submission,
                                            **kwargs):
        problem_instance = submission.problem_instance
        problem = problem_instance.problem
        contest = problem_instance.contest
        if contest is not None:
            round = problem_instance.round

        submission = submission.programsubmission
        environ['source_file'] = \
            django_to_filetracker_path(submission.source_file)
        environ['language'] = problem_instance.controller \
            ._get_language(submission.source_file, problem_instance)
        environ['compilation_result_size_limit'] = \
            problem_instance.controller \
                .get_compilation_result_size_limit(submission)

        environ['submission_id'] = submission.id
        environ['submission_kind'] = submission.kind
        environ['problem_instance_id'] = problem_instance.id
        environ['problem_id'] = problem.id
        environ['problem_short_name'] = problem.short_name
        if contest is not None:
            environ['round_id'] = round.id
            environ['contest_id'] = contest.id
        environ['submission_owner'] = submission.user.username \
                                      if submission.user else None

        environ.setdefault('report_kinds', ['INITIAL', 'NORMAL'])
        if 'hidden_judge' in environ['extra_args']:
            environ['report_kinds'] = ['HIDDEN']

    def generate_base_environ(self, environ, submission, **kwargs):
        self.generate_initial_evaluation_environ(environ, submission)
        environ['recipe'] = [
                ('compile',
                    'oioioi.programs.handlers.compile'),
                ('compile_end',
                    'oioioi.programs.handlers.compile_end'),

                recipe_placeholder('after_compile'),

                ('delete_executable',
                    'oioioi.programs.handlers.delete_executable'),
            ]
        environ['error_handlers'] = [('delete_executable',
                    'oioioi.programs.handlers.delete_executable')]

        if getattr(settings, 'USE_UNSAFE_EXEC', False):
            environ['exec_mode'] = 'unsafe'
        else:
            environ['exec_mode'] = settings.SAFE_EXEC_MODE

        if getattr(settings, 'USE_LOCAL_COMPILERS', False):
            environ['compiler'] = 'system-' + environ['language']

    def generate_recipe(self, kinds):
        recipe_body = [
                ('collect_tests',
                'oioioi.programs.handlers.collect_tests'),
        ]

        if 'INITIAL' in kinds:
            recipe_body.extend(
                [
                    ('initial_run_tests',
                        'oioioi.programs.handlers.run_tests',
                        dict(kind='EXAMPLE')),
                    ('initial_run_tests_end',
                        'oioioi.programs.handlers.run_tests_end'),
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
                ])

        if 'USER_OUTS' in kinds:
            recipe_body.extend(
                [
                    ('userout_run_tests',
                        'oioioi.programs.handlers.run_tests',
                        dict(kind=None)),
                    ('userout_run_tests',
                        'oioioi.programs.handlers.run_tests_end'),
                    ('userout_grade_tests',
                        'oioioi.programs.handlers.grade_tests'),
                    ('userout_grade_groups',
                        'oioioi.programs.handlers.grade_groups'),
                    ('userout_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None)),
                    ('userout_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='USER_OUTS', save_scores=False)),
                    ('userout_fill_outfile_in_existing_test_reports',
                        'oioioi.programs.handlers.'
                        'fill_outfile_in_existing_test_reports'),
                    ('userout_insert_existing_submission_link',
                        'oioioi.programs.handlers.'
                        'insert_existing_submission_link'),
                ])

        if 'NORMAL' in kinds or 'HIDDEN' in kinds or 'FULL' in kinds:
            recipe_body.append(recipe_placeholder('before_final_tests'))

        if 'NORMAL' in kinds:
            recipe_body.extend(
                [
                    ('final_run_tests',
                        'oioioi.programs.handlers.run_tests',
                        dict(kind='NORMAL')),
                    ('final_run_tests_end',
                        'oioioi.programs.handlers.run_tests_end'),
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
                    ('hidden_run_tests',
                        'oioioi.programs.handlers.run_tests'),
                    ('hidden_run_tests_end',
                        'oioioi.programs.handlers.run_tests_end'),
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

        if 'FULL' in kinds:
            recipe_body.extend(
                [
                    ('full_run_tests',
                        'oioioi.programs.handlers.run_tests'),
                    ('full_run_tests',
                        'oioioi.programs.handlers.run_tests_end'),
                    ('full_grade_tests',
                        'oioioi.programs.handlers.grade_tests'),
                    ('full_grade_groups',
                        'oioioi.programs.handlers.grade_groups'),
                    ('full_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None)),
                    ('full_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='FULL')),
                    recipe_placeholder('after_full_tests'),
                ])

        return recipe_body

    def get_compilation_result_size_limit(self, submission):
        return 10 * 1024 * 1024

    def _get_language(self, source_file, problem_instance):
        return os.path.splitext(source_file.name)[1][1:]

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        self.generate_base_environ(environ, submission, **kwargs)

        if 'USER_OUTS' in environ['submission_kind']:
            environ['report_kinds'] = ['USER_OUTS']
            environ['save_outputs'] = True

        recipe_body = self.generate_recipe(environ['report_kinds'])

        extend_after_placeholder(environ, 'after_compile', recipe_body)

        environ.setdefault('group_scorer',
                            'oioioi.programs.utils.min_group_scorer')
        environ.setdefault('score_aggregator',
                'oioioi.programs.utils.sum_score_aggregator')

        checker = OutputChecker.objects.get(problem=self.problem).exe_file
        if checker:
            environ['checker'] = django_to_filetracker_path(checker)

        if 'INITIAL' in environ['report_kinds']:
            add_before_placeholder(environ, 'after_initial_tests',
                    ('update_report_statuses',
                        'oioioi.contests.handlers.update_report_statuses'))
            add_before_placeholder(environ, 'after_initial_tests',
                    ('update_submission_score',
                        'oioioi.contests.handlers.update_submission_score'))

    def _map_report_to_submission_status(self, status, problem_instance,
                                         kind='INITIAL'):
        if kind == 'INITIAL':
            mapping = {'OK': 'INI_OK', 'CE': 'CE', 'SE': 'SE'}
            return mapping.get(status, 'INI_ERR')
        return status

    def update_submission_score(self, submission):
        # Status is taken from User_outs report when generating user out
        if submission.kind == 'USER_OUTS':
            kind_for_status = 'USER_OUTS'
        # Otherwise from the Initial report
        else:
            kind_for_status = 'INITIAL'

        try:
            report = SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind=kind_for_status).get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.status = submission.problem_instance.controller \
                ._map_report_to_submission_status(
                    score_report.status, submission.problem_instance,
                    kind=kind_for_status)
        except SubmissionReport.DoesNotExist:
            if SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind='FAILURE'):
                submission.status = 'SE'
            else:
                submission.status = '?'

        # Score from the final
        try:
            report = SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind='NORMAL').get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.score = score_report.score
        except SubmissionReport.DoesNotExist:
            submission.score = None

        submission.save()

    def filter_allowed_languages_dict(self, languages, problem_instance):
        return languages

    def get_submission_size_limit(self, problem_instance):
        return 102400  # in bytes

    def get_allowed_languages_dict(self, problem_instance):
        return getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})

    def get_allowed_languages(self, problem_instance):
        return problem_instance.controller \
            .get_allowed_languages_dict(problem_instance).keys()

    def get_allowed_extensions(self, problem_instance):
        lang_exts = problem_instance.controller \
            .get_allowed_languages_dict(problem_instance).values()
        return [ext for lang in lang_exts for ext in lang]

    def parse_language_by_extension(self, ext, problem_instance):
        for lang, extension_list in problem_instance.controller \
                .get_allowed_languages_dict(problem_instance).items():
            if ext in extension_list:
                return lang
        return None

    def check_repeated_submission(self, request, problem_instance, form):
        return not is_problem_author(request, problem_instance.problem) \
                and form.kind == 'NORMAL' and \
                getattr(settings, 'WARN_ABOUT_REPEATED_SUBMISSION', False)

    def validate_submission_form(self, request, problem_instance, form,
            cleaned_data):
        is_file_chosen = 'file' in cleaned_data and \
                cleaned_data['file'] is not None
        is_code_pasted = 'code' in cleaned_data and cleaned_data['code']

        if (not is_file_chosen and not is_code_pasted) or \
                (is_file_chosen and is_code_pasted):
            raise ValidationError(_("You have to either choose file or paste "
                "code."))

        if 'prog_lang' not in cleaned_data:
            cleaned_data['prog_lang'] = None

        if not cleaned_data['prog_lang'] and is_file_chosen:
            ext = os.path.splitext(cleaned_data['file'].name)[1].strip('.')
            cleaned_data['prog_lang'] = problem_instance.controller \
                .parse_language_by_extension(ext, problem_instance)

        if not cleaned_data['prog_lang']:
            if is_code_pasted:
                raise ValidationError(_("You have to choose programming "
                                        "language."))
            else:
                raise ValidationError(_("Unrecognized file extension."))

        problem_instance = cleaned_data['problem_instance']
        controller = problem_instance.controller
        langs = controller.filter_allowed_languages_dict(
                controller.get_allowed_languages_dict(problem_instance),
                problem_instance)
        if cleaned_data['prog_lang'] not in langs.keys():
            raise ValidationError(_("This language is not allowed for selected"
                                    " problem."))

        if is_file_chosen:
            code = cleaned_data['file'].read()
        else:
            code = cleaned_data['code'].encode('utf-8')

        if problem_instance.controller \
                .check_repeated_submission(request, problem_instance, form):
            lines = iter(code.splitlines())
            md5 = hashlib.md5()
            for line in lines:
                md5.update(line)
            md5 = md5.hexdigest()
            session_md5_key = 'programs_%d_md5' % \
                    cleaned_data['problem_instance'].id

            if session_md5_key in request.session and \
                    md5 == request.session[session_md5_key]:
                del request.session[session_md5_key]
                raise ValidationError(
                    _("You have submitted the same file for this problem "
                      "again. Please resubmit if you really want "
                      "to submit the same file"))
            else:
                request.session[session_md5_key] = md5
                request.session.save()

        return cleaned_data

    def mixins_for_admin(self):
        from oioioi.programs.admin import ProgrammingProblemAdminMixin
        return super(ProgrammingProblemController, self).mixins_for_admin() \
                + (ProgrammingProblemAdminMixin,)

    def create_submission(self, request, problem_instance, form_data,
                    judge_after_create=True, **kwargs):
        submission = ProgramSubmission(
                user=form_data.get('user', request.user),
                problem_instance=problem_instance,
                kind=form_data.get('kind',
                    problem_instance.controller.get_default_submission_kind(
                           request, problem_instance=problem_instance)),
                    date=request.timestamp
        )

        file = form_data['file']
        if file is None:
            lang_exts = getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})
            extension = lang_exts[form_data['prog_lang']][0]
            file = ContentFile(form_data['code'], '__pasted_code.' + extension)

        submission.source_file.save(file.name, file)
        submission.save()
        if judge_after_create:
            problem_instance.controller.judge(submission)
        return submission

    def adjust_submission_form(self, request, form, problem_instance):
        controller = problem_instance.controller
        size_limit = controller.get_submission_size_limit(problem_instance)

        def validate_file_size(file):
            if file.size > size_limit:
                raise ValidationError(_("File size limit exceeded."))

        def validate_language(file):
            ext = controller._get_language(file, problem_instance)
            if ext not in controller.get_allowed_extensions(problem_instance):
                raise ValidationError(_(
                    "Unknown or not supported file extension."))

        def parse_problem(problem):
            available_problems = form.fields['problem_instance_id'].choices
            problem_id = None
            for (id, name) in available_problems:
                if name.find(problem) != -1:
                    if problem_id is None:
                        problem_id = id
                    else:
                        # matched more than one available problem
                        return None
            return problem_id

        form.fields['file'] = forms.FileField(required=False,
                allow_empty_file=False,
                validators=[validate_file_size, validate_language],
                label=_("File"),
                help_text=mark_safe(_(
                    "Language is determined by the file extension."
                    " It has to be one of: %s."
                    " You can paste the code below instead of"
                    " choosing file."
                    " <strong>Try drag-and-drop too!</strong>"
                ) % (', '.join(controller.get_allowed_extensions(
                        problem_instance))))
        )
        form.fields['code'] = forms.CharField(required=False,
                label=_("Code"),
                widget=forms.widgets.Textarea(attrs={'rows': 10,
                    'class': 'monospace input-xxxlarge'})
        )

        choices = [('', '')]
        choices += [(lang, lang) for lang in controller.get_allowed_languages(
                problem_instance)]
        form.fields['prog_lang'] = forms.ChoiceField(required=False,
                label=_("Programming language"),
                choices=choices,
                widget=forms.Select(attrs={'disabled': 'disabled'})
        )

        if 'dropped_solution' in request.POST:
            form.fields['code'].initial = request.POST['dropped_solution']

        # guessing problem name and extension when file dragged and dropped
        if 'dropped_solution_name' in request.POST:
            # do not validate blank fields this time
            form.is_bound = False

            fname = request.POST['dropped_solution_name']
            if fname.count('.') == 1:
                [problem, ext] = fname.split('.', 1)
                if 'problem_instance_id' not in request.POST:
                    form.fields['problem_instance_id'].initial = \
                            parse_problem(problem)
                if 'prog_lang' not in request.POST:
                    form.fields['prog_lang'].initial = \
                            controller.parse_language_by_extension(ext)

        if request.contest and is_contest_admin(request):
            form.fields['user'] = UserSelectionField(
                    label=_("User"),
                    hints_url=reverse('contest_user_hints',
                            kwargs={'contest_id': request.contest.id}),
                    initial=request.user)

            def clean_user():
                try:
                    user = form.cleaned_data['user']
                    if user == request.user:
                        return user
                    if not request.user.is_superuser:
                        controller.registration_controller() \
                            .filter_participants(
                                User.objects.filter(pk=user.pk)).get()
                    return user
                except User.DoesNotExist:
                    raise forms.ValidationError(_(
                            "User does not exist or "
                            "you do not have enough privileges"))
            form.clean_user = clean_user
            form.fields['kind'] = forms.ChoiceField(choices=[
                ('NORMAL', _("Normal")), ('IGNORED', _("Ignored"))],
                initial=form.kind, label=_("Kind"))

    def render_submission(self, request, submission):
        problem_instance = submission.problem_instance
        if submission.kind == 'USER_OUTS':
            # The comment includes safe string, because it is generated
            # automatically (users can not affect it).
            # Note that we temporarily assign a safestring object, because
            # field type in model is originally a string.
            submission.programsubmission.comment = \
                mark_safe(submission.programsubmission.comment)

        return render_to_string('programs/submission_header.html',
                context_instance=RequestContext(request,
                    {'submission': submission_template_context(request,
                        submission.programsubmission),
                    'saved_diff_id': request.session.get('saved_diff_id'),
                    'supported_extra_args':
                        problem_instance.controller.get_supported_extra_args(
                            submission)}))

    def render_report_failure(self, request, report):
        return ProblemController.render_report(self, request, report)

    def is_admin(self, request, report):
        return is_problem_author(request, self.problem)

    def render_report(self, request, report):
        problem_instance = report.submission.problem_instance
        if report.kind == 'FAILURE':
            return problem_instance.controller \
                    .render_report_failure(request, report)

        score_report = ScoreReport.objects.get(submission_report=report)
        compilation_report = \
                CompilationReport.objects.get(submission_report=report)
        test_reports = TestReport.objects.filter(submission_report=report) \
                .order_by('test__order', 'test_group', 'test_name')
        group_reports = GroupReport.objects.filter(submission_report=report)
        show_scores = any(gr.score is not None for gr in group_reports)
        group_reports = dict((g.group, g) for g in group_reports)

        picontroller = problem_instance.controller

        allow_download_out = picontroller \
                                .can_generate_user_out(request, report)
        allow_test_comments = picontroller \
                                .can_see_test_comments(request, report)
        all_outs_generated = allow_download_out

        groups = []
        for group_name, tests in itertools.groupby(test_reports,
                attrgetter('test_group')):
            tests_list = list(tests)
            groups.append({'tests': tests_list,
                'report': group_reports[group_name]})

            for test in tests_list:
                test.generate_status = picontroller \
                    ._out_generate_status(request, test)
                all_outs_generated &= (test.generate_status == 'OK')

        return render_to_string('programs/report.html',
                context_instance=RequestContext(request,
                    {'report': report, 'score_report': score_report,
                        'compilation_report': compilation_report,
                        'groups': groups, 'show_scores': show_scores,
                        'allow_download_out': allow_download_out,
                        'allow_test_comments': allow_test_comments,
                        'all_outs_generated': all_outs_generated,
                        'is_admin': picontroller.is_admin(request, report)}))

    def can_generate_user_out(self, request, submission_report):
        """Determines if the current user is allowed to generate outs from
           ``submission_report``.

           Default implementations allow only problem author.
        """
        problem = submission_report.submission.problem_instance.problem
        return is_problem_author(request, problem)

    def can_see_source(self, request, submission):
        return can_see_submission_without_contest(request, submission)

    def can_see_test_comments(self, request, submissionreport):
        return True

    def _out_generate_status(self, request, testreport):
        problem = testreport.test.problem_instance.problem
        try:
            if is_problem_author(request, problem) or \
                    testreport.userout_status.visible_for_user:
                # making sure, that output really exists or is processing
                if bool(testreport.output_file) or \
                        testreport.userout_status.status == '?':
                    return testreport.userout_status.status

        except UserOutGenStatus.DoesNotExist:
            if testreport.output_file:
                return 'OK'

        return None


class ProgrammingContestController(ContestController):
    description = _("Simple programming contest")

    def _map_report_to_submission_status(self, status, problem_instance,
                                         kind='INITIAL'):
        return problem_instance.problem.controller \
            ._map_report_to_submission_status(status, problem_instance, kind)

    def filter_allowed_languages_dict(self, languages, problem_instance):
        return problem_instance.problem.controller \
            .filter_allowed_languages_dict(languages, problem_instance)

    def get_compilation_result_size_limit(self, submission):
        return submission.problem_instance.problem.controller \
            .get_compilation_result_size_limit(submission)

    def _get_language(self, source_file, problem_instance):
        return problem_instance.problem.controller \
            ._get_language(source_file, problem_instance)

    def use_spliteval(self, submission):
        return True

    def fill_evaluation_environ(self, environ, submission):
        problem = submission.problem_instance.problem
        problem.controller.fill_evaluation_environ(environ, submission)
        self.fill_evaluation_environ_post_problem(environ, submission)

    def fill_evaluation_environ_post_problem(self, environ, submission):
        """Run after ProblemController.fill_evaluation_environ."""
        if 'INITIAL' in environ['report_kinds']:
            add_before_placeholder(environ, 'after_initial_tests',
                    ('update_report_statuses',
                        'oioioi.contests.handlers.update_report_statuses'))
            add_before_placeholder(environ, 'after_initial_tests',
                    ('update_submission_score',
                        'oioioi.contests.handlers.update_submission_score'))

    def create_submission(self, request, problem_instance, form_data,
                    judge_after_create=True, **kwargs):
        problem = problem_instance.problem
        return problem.controller.create_submission(request,
                problem_instance, form_data, judge_after_create=True, **kwargs)

    def get_submission_size_limit(self, problem_instance):
        return problem_instance.problem.controller \
            .get_submission_size_limit(problem_instance)

    def get_allowed_languages_dict(self, problem_instance):
        return problem_instance.problem.controller \
            .get_allowed_languages_dict(problem_instance)

    def get_allowed_languages(self, problem_instance):
        return problem_instance.problem.controller \
            .get_allowed_languages(problem_instance)

    def get_allowed_extensions(self, problem_instance):
        return problem_instance.problem.controller \
            .get_allowed_extensions(problem_instance)

    def parse_language_by_extension(self, ext, problem_instance):
        return problem_instance.problem.controller \
            .parse_language_by_extension(ext, problem_instance)

    def adjust_submission_form(self, request, form, problem_instance):
        super(ProgrammingContestController, self) \
                  .adjust_submission_form(request, form, problem_instance)
        problem_instance.problem.controller \
                .adjust_submission_form(request, form, problem_instance)

    def check_repeated_submission(self, request, problem_instance, form):
        return not is_contest_admin(request) and \
            form.kind == 'NORMAL' and \
            getattr(settings, 'WARN_ABOUT_REPEATED_SUBMISSION', False)

    def validate_submission_form(self, request, problem_instance, form,
            cleaned_data):
        return problem_instance.problem.controller \
            .validate_submission_form(request, problem_instance,
                                      form, cleaned_data)

    def update_report_statuses(self, submission, queryset):
        """Updates statuses of reports for the newly judged submission.

           Usually this involves looking at reports and deciding which should
           be ``ACTIVE`` and which should be ``SUPERSEDED``.

           :param submission: an instance of
                              :class:`oioioi.contests.models.Submission`
           :param queryset: a queryset returning reports for the submission
        """
        controller = submission.problem_instance.controller
        controller._activate_newest_report(submission, queryset,
                kind=['NORMAL', 'FAILURE'])
        controller._activate_newest_report(submission, queryset,
                kind=['INITIAL'])
        controller._activate_newest_report(submission, queryset,
                kind=['USER_OUTS'])

    def can_see_submission_status(self, request, submission):
        """Statuses are taken from initial tests which are always public."""
        return True

    def update_submission_score(self, submission):
        problem = submission.problem_instance.problem
        problem.controller.update_submission_score(submission)

    def get_visible_reports_kinds(self, request, submission):
        if self.results_visible(request, submission):
            return ['USER_OUTS', 'INITIAL', 'NORMAL']
        else:
            return ['USER_OUTS', 'INITIAL']

    def filter_visible_reports(self, request, submission, queryset):
        if is_contest_admin(request) or is_contest_observer(request):
            return queryset
        return queryset.filter(status='ACTIVE',
                kind__in=self.get_visible_reports_kinds(request, submission))

    def filter_my_visible_submissions(self, request, queryset):
        if not is_contest_admin(request):
            queryset = queryset.exclude(kind='USER_OUTS')
        return super(ProgrammingContestController, self). \
                filter_my_visible_submissions(request, queryset)

    def can_generate_user_out(self, request, submission_report):
        """Determines if the current user is allowed to generate outs from
           ``submission_report``.

           Default implementations delegates to
           ``report_actions_config`` associated with the problem,
           :meth:`~ContestController.can_see_problem`,
           :meth:`~ContestController.filter_my_visible_submissions`,
           except for admins and observers, which get full access.
        """
        submission = submission_report.submission
        if is_contest_admin(request) or is_contest_observer(request):
            return True
        if not has_report_actions_config(submission.problem_instance.problem):
            return False
        config = submission.problem_instance.problem.report_actions_config

        return (config.can_user_generate_outs and
                submission.user == request.user and
                self.can_see_problem(request, submission.problem_instance) and
                self.filter_visible_reports(request, submission,
                    SubmissionReport.objects.filter(id=submission_report.id))
                    .exists())

    def filter_visible_sources(self, request, queryset):
        """Determines which sources the user could see.

           This usually involves cross-user privileges, like publicizing
           sources. Default implementations delegates to
           :meth:`~ContestController.filter_my_visible_submissions`, except for
           admins and observers, which get full access.

           Queryset's model should be oioioi.contest.Submission
        """
        if is_contest_admin(request) or is_contest_observer(request):
            return queryset
        return self.filter_my_visible_submissions(request, queryset)

    def can_see_source(self, request, submission):
        """Check if submission's source should be visible.
           :type submission: oioioi.contest.Submission

           Consider using filter_visible_sources instead, especially for batch
           queries.
        """
        qs = Submission.objects.filter(id=submission.id)
        return self.filter_visible_sources(request, qs).exists()

    def render_submission(self, request, submission):
        problem = submission.problem_instance.problem
        return problem.controller.render_submission(request, submission)

    def _out_generate_status(self, request, testreport):
        try:
            if is_contest_admin(request) or \
                    testreport.userout_status.visible_for_user:
                # making sure, that output really exists or is processing
                if bool(testreport.output_file) or \
                        testreport.userout_status.status == '?':
                    return testreport.userout_status.status

        except UserOutGenStatus.DoesNotExist:
            if testreport.output_file:
                return 'OK'

        return None

    def can_see_test_comments(self, request, submissionreport):
        return submissionreport.submission.problem_instance.problem \
            .controller.can_see_test_comments(request, submissionreport)

    def render_report_failure(self, request, report):
        return ContestController.render_report(self, request, report)

    def is_admin(self, request, report):
        return is_contest_admin(request)

    def render_report(self, request, report):
        return report.submission.problem_instance.problem.controller \
            .render_report(request, report)

    def render_submission_footer(self, request, submission):
        super_footer = super(ProgrammingContestController, self). \
                render_submission_footer(request, submission)
        queryset = Submission.objects \
                .filter(problem_instance__contest=request.contest) \
                .filter(user=submission.user) \
                .filter(problem_instance=submission.problem_instance) \
                .exclude(pk=submission.pk) \
                .order_by('-date') \
                .select_related()
        if not is_contest_admin(request):
            cc = request.contest.controller
            queryset = cc.filter_my_visible_submissions(request, queryset)
        show_scores = bool(queryset.filter(score__isnull=False))
        if not queryset.exists():
            return super_footer
        return super_footer + render_to_string(
                'programs/other_submissions.html',
                context_instance=RequestContext(request, {
                        'submissions': [submission_template_context(request, s)
                                 for s in queryset],
                        'show_scores': show_scores,
                        'main_submission_id': submission.id,
                        'submissions_on_page': getattr(settings,
                            'SUBMISSIONS_ON_PAGE', 15)}))

    def valid_kinds_for_submission(self, submission):
        if ModelProgramSubmission.objects.filter(id=submission.id).exists():
            return [submission.kind]

        if submission.kind == 'USER_OUTS':
            return ['USER_OUTS']

        return super(ProgrammingContestController, self) \
                .valid_kinds_for_submission(submission)
