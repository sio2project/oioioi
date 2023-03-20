import hashlib
import itertools
import logging
from operator import attrgetter  # pylint: disable=E0611

from django import forms
from django.conf import settings
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.core.files.base import ContentFile
from django.forms.widgets import Media
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.base.preferences import ensure_preferences_exist_for_user
from oioioi.base.utils.inputs import narrow_input_field
from oioioi.base.widgets import AceEditorWidget
from oioioi.contests.controllers import ContestController, submission_template_context
from oioioi.contests.models import ScoreReport, SubmissionReport
from oioioi.contests.utils import (
    is_contest_admin,
    is_contest_basicadmin,
    is_contest_observer,
)
from oioioi.evalmgr.tasks import (
    add_before_placeholder,
    extend_after_placeholder,
    recipe_placeholder,
)
from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.problems.controllers import ProblemController
from oioioi.problems.utils import can_admin_problem, can_admin_problem_instance
from oioioi.programs.models import (
    CompilationReport,
    ContestCompiler,
    GroupReport,
    ModelProgramSubmission,
    OutputChecker,
    ProblemAllowedLanguage,
    ProblemCompiler,
    ProgramSubmission,
    Submission,
    TestReport,
    UserOutGenStatus,
)
from oioioi.programs.problem_instance_utils import (
    get_allowed_languages_dict,
    get_allowed_languages_extensions,
    get_language_by_extension,
)
from oioioi.programs.utils import (
    filter_model_submissions,
    form_field_id_for_langs,
    get_extension,
    get_problem_link_or_name,
    has_report_actions_config,
    is_model_submission,
    get_submittable_languages,
)
from oioioi.programs.widgets import CancellableFileInput


logger = logging.getLogger(__name__)

def get_report_display_type(request, test_report):
    if test_report.status == 'INI_OK' or test_report.status == 'OK':
        try:
            if test_report.score is None or test_report.max_score is None:
                display_type = test_report.status

            elif test_report.max_score.to_int() == 0:
                display_type = test_report.status

            else:
                score_percentage = (
                    float(test_report.score.to_int()) / test_report.max_score.to_int()
                )

                if score_percentage < 0.25:
                    display_type = 'OK0'
                elif score_percentage < 0.5:
                    display_type = 'OK25'
                elif score_percentage < 0.75:
                    display_type = 'OK50'
                elif score_percentage < 1.0:
                    display_type = 'OK75'
                else:
                    display_type = 'OK100'

        # If by any means there is no 'score' or 'max_score' field then
        # we just treat the test report as without them
        except AttributeError:
            display_type = test_report.status

    else:
        display_type = test_report.status

    return display_type

class ProgrammingProblemController(ProblemController):
    description = _("Simple programming problem")

    def get_compiler_for_submission(self, submission):
        problem_instance = submission.problem_instance
        extension = get_extension(submission.source_file.name)
        language = get_language_by_extension(problem_instance, extension)
        assert language

        compiler = problem_instance.controller.get_compiler_for_language(
            problem_instance, language
        )
        if compiler is not None:
            return compiler
        else:
            logger.warning("No default compiler for language %s", language)
            return 'default-' + extension

    def get_compiler_for_language(self, problem_instance, language):
        problem = problem_instance.problem
        problem_compiler_qs = ProblemCompiler.objects.filter(
            problem__exact=problem.id, language__exact=language
        )
        if problem_compiler_qs.exists():
            return problem_compiler_qs.first().compiler
        else:
            default_compilers = getattr(settings, 'DEFAULT_COMPILERS')
            compiler = default_compilers.get(language)
            if compiler is not None:
                return compiler
            else:
                return None

    def generate_initial_evaluation_environ(self, environ, submission, **kwargs):
        problem_instance = submission.problem_instance
        problem = problem_instance.problem
        contest = problem_instance.contest
        if contest is not None:
            round = problem_instance.round

        submission = submission.programsubmission
        environ['source_file'] = django_to_filetracker_path(submission.source_file)
        environ['language'] = get_extension(submission.source_file.name)
        environ[
            'compilation_result_size_limit'
        ] = problem_instance.controller.get_compilation_result_size_limit(submission)

        environ['submission_id'] = submission.id
        environ['submission_kind'] = submission.kind
        environ['problem_instance_id'] = problem_instance.id
        environ['problem_id'] = problem.id
        environ['problem_short_name'] = problem.short_name
        if contest is not None:
            environ['round_id'] = round.id
            environ['contest_id'] = contest.id
        environ['submission_owner'] = (
            submission.user.username if submission.user else None
        )
        environ['oioioi_instance'] = settings.SITE_NAME
        environ['contest_priority'] = (
            contest.judging_priority
            if contest is not None
            else settings.NON_CONTEST_PRIORITY
        )
        environ['contest_priority'] += settings.OIOIOI_INSTANCE_PRIORITY_BONUS
        environ['contest_weight'] = (
            contest.judging_weight
            if contest is not None
            else settings.NON_CONTEST_WEIGHT
        )
        environ['contest_weight'] += settings.OIOIOI_INSTANCE_WEIGHT_BONUS

        environ.setdefault('report_kinds', ['INITIAL', 'NORMAL']),
        if 'hidden_judge' in environ['extra_args']:
            environ['report_kinds'] = ['HIDDEN']

        environ['compiler'] = problem_instance.controller.get_compiler_for_submission(
            submission
        )

    def generate_base_environ(self, environ, submission, **kwargs):
        contest = submission.problem_instance.contest
        self.generate_initial_evaluation_environ(environ, submission)
        environ.setdefault('recipe', []).extend(
            [
                ('compile', 'oioioi.programs.handlers.compile'),
                ('compile_end', 'oioioi.programs.handlers.compile_end'),
                recipe_placeholder('after_compile'),
                ('delete_executable', 'oioioi.programs.handlers.delete_executable'),
            ]
        )
        environ.setdefault('error_handlers', []).append(
            ('delete_executable', 'oioioi.programs.handlers.delete_executable')
        )

        if getattr(settings, 'USE_UNSAFE_EXEC', False):
            environ['exec_mode'] = 'unsafe'
        else:
            environ[
                'exec_mode'
            ] = submission.problem_instance.controller.get_safe_exec_mode()

        environ['untrusted_checker'] = not settings.USE_UNSAFE_CHECKER

    def generate_recipe(self, kinds):
        recipe_body = [('collect_tests', 'oioioi.programs.handlers.collect_tests')]

        if 'INITIAL' in kinds:
            recipe_body.extend(
                [
                    (
                        'initial_run_tests',
                        'oioioi.programs.handlers.run_tests',
                        dict(kind='EXAMPLE'),
                    ),
                    ('initial_run_tests_end', 'oioioi.programs.handlers.run_tests_end'),
                    ('initial_grade_tests', 'oioioi.programs.handlers.grade_tests'),
                    ('initial_grade_groups', 'oioioi.programs.handlers.grade_groups'),
                    (
                        'initial_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind='EXAMPLE'),
                    ),
                    (
                        'initial_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='INITIAL'),
                    ),
                    recipe_placeholder('after_initial_tests'),
                ]
            )

        if 'USER_OUTS' in kinds:
            recipe_body.extend(
                [
                    (
                        'userout_run_tests',
                        'oioioi.programs.handlers.run_tests',
                        dict(kind=None),
                    ),
                    ('userout_run_tests', 'oioioi.programs.handlers.run_tests_end'),
                    ('userout_grade_tests', 'oioioi.programs.handlers.grade_tests'),
                    ('userout_grade_groups', 'oioioi.programs.handlers.grade_groups'),
                    (
                        'userout_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None),
                    ),
                    (
                        'userout_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='USER_OUTS', save_scores=False),
                    ),
                    (
                        'userout_fill_outfile_in_existing_test_reports',
                        'oioioi.programs.handlers.'
                        'fill_outfile_in_existing_test_reports',
                    ),
                    (
                        'userout_insert_existing_submission_link',
                        'oioioi.programs.handlers.' 'insert_existing_submission_link',
                    ),
                ]
            )

        if 'NORMAL' in kinds or 'HIDDEN' in kinds or 'FULL' in kinds:
            recipe_body.append(recipe_placeholder('before_final_tests'))

        if 'NORMAL' in kinds:
            recipe_body.extend(
                [
                    (
                        'final_run_tests',
                        'oioioi.programs.handlers.run_tests',
                        dict(kind='NORMAL'),
                    ),
                    ('final_run_tests_end', 'oioioi.programs.handlers.run_tests_end'),
                    ('final_grade_tests', 'oioioi.programs.handlers.grade_tests'),
                    ('final_grade_groups', 'oioioi.programs.handlers.grade_groups'),
                    (
                        'final_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                    ),
                    ('final_make_report', 'oioioi.programs.handlers.make_report'),
                    recipe_placeholder('after_final_tests'),
                ]
            )

        if 'HIDDEN' in kinds:
            recipe_body.extend(
                [
                    ('hidden_run_tests', 'oioioi.programs.handlers.run_tests'),
                    ('hidden_run_tests_end', 'oioioi.programs.handlers.run_tests_end'),
                    ('hidden_grade_tests', 'oioioi.programs.handlers.grade_tests'),
                    ('hidden_grade_groups', 'oioioi.programs.handlers.grade_groups'),
                    (
                        'hidden_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None),
                    ),
                    (
                        'hidden_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='HIDDEN'),
                    ),
                    recipe_placeholder('after_all_tests'),
                ]
            )

        if 'FULL' in kinds:
            recipe_body.extend(
                [
                    ('full_run_tests', 'oioioi.programs.handlers.run_tests'),
                    ('full_run_tests', 'oioioi.programs.handlers.run_tests_end'),
                    ('full_grade_tests', 'oioioi.programs.handlers.grade_tests'),
                    ('full_grade_groups', 'oioioi.programs.handlers.grade_groups'),
                    (
                        'full_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None),
                    ),
                    (
                        'full_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='FULL'),
                    ),
                    recipe_placeholder('after_full_tests'),
                ]
            )

        return recipe_body

    def get_compilation_result_size_limit(self, submission):
        return 10 * 1024 * 1024

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        self.generate_base_environ(environ, submission, **kwargs)

        if 'USER_OUTS' in environ['submission_kind']:
            environ['report_kinds'] = ['USER_OUTS']
            environ['save_outputs'] = True

        recipe_body = self.generate_recipe(environ['report_kinds'])

        extend_after_placeholder(environ, 'after_compile', recipe_body)

        environ.setdefault('group_scorer', 'oioioi.programs.utils.min_group_scorer')
        environ.setdefault(
            'score_aggregator', 'oioioi.programs.utils.sum_score_aggregator'
        )

        checker = OutputChecker.objects.get(problem=self.problem).exe_file
        if checker:
            environ['checker'] = django_to_filetracker_path(checker)

        if 'INITIAL' in environ['report_kinds']:
            add_before_placeholder(
                environ,
                'after_initial_tests',
                (
                    'update_report_statuses',
                    'oioioi.contests.handlers.update_report_statuses',
                ),
            )
            add_before_placeholder(
                environ,
                'after_initial_tests',
                (
                    'update_submission_score',
                    'oioioi.contests.handlers.update_submission_score',
                ),
            )

    def _map_report_to_submission_status(
        self, status, problem_instance, kind='INITIAL'
    ):
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
            report = SubmissionReport.objects.filter(
                submission=submission, status='ACTIVE', kind=kind_for_status
            ).get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.status = (
                submission.problem_instance.controller._map_report_to_submission_status(
                    score_report.status,
                    submission.problem_instance,
                    kind=kind_for_status,
                )
            )
        except SubmissionReport.DoesNotExist:
            if SubmissionReport.objects.filter(
                submission=submission, status='ACTIVE', kind='FAILURE'
            ):
                submission.status = 'SE'
            else:
                submission.status = '?'

        # Score from the final
        try:
            report = SubmissionReport.objects.filter(
                submission=submission, status='ACTIVE', kind='NORMAL'
            ).get()
            score_report = ScoreReport.objects.get(submission_report=report)
            submission.score = score_report.score
        except SubmissionReport.DoesNotExist:
            submission.score = None

        submission.save()

    def get_submission_size_limit(self, problem_instance):
        return 102400  # in bytes

    def check_repeated_submission(self, request, problem_instance, form):
        return (
            not can_admin_problem(request, problem_instance.problem)
            and form.kind == 'NORMAL'
            and getattr(settings, 'WARN_ABOUT_REPEATED_SUBMISSION', False)
        )

    def validate_submission_form(self, request, problem_instance, form, cleaned_data):
        if any(field in form.errors.as_data() for field in ('file', 'code')):
            return  # already have a ValidationError

        is_file_chosen = 'file' in cleaned_data and cleaned_data['file'] is not None
        is_code_pasted = 'code' in cleaned_data and cleaned_data['code']

        if (not is_file_chosen and not is_code_pasted) or (
            is_file_chosen and is_code_pasted
        ):
            raise ValidationError(_("You have to either choose file or paste code."))

        langs_field_name = form_field_id_for_langs(problem_instance)
        if langs_field_name not in cleaned_data:
            cleaned_data[langs_field_name] = None

        if not cleaned_data[langs_field_name] and is_file_chosen:
            ext = get_extension(cleaned_data['file'].name)
            cleaned_data[langs_field_name] = get_language_by_extension(
                problem_instance, ext
            )

        if not cleaned_data[langs_field_name]:
            if is_code_pasted:
                raise ValidationError(_("You have to choose programming language."))
            else:
                raise ValidationError(_("Unrecognized file extension."))

        langs = get_allowed_languages_dict(problem_instance)
        if cleaned_data[langs_field_name] not in langs.keys():
            raise ValidationError(
                _("This language is not allowed for selected problem.")
            )

        if is_file_chosen:
            code = cleaned_data['file'].read()
        else:
            code = cleaned_data['code'].encode('utf-8')

        if problem_instance.controller.check_repeated_submission(
            request, problem_instance, form
        ):
            lines = iter(code.splitlines())
            md5 = hashlib.md5()
            for line in lines:
                md5.update(line)
            md5 = md5.hexdigest()
            session_md5_key = 'programs_%d_md5' % cleaned_data['problem_instance'].id

            if (
                session_md5_key in request.session
                and md5 == request.session[session_md5_key]
            ):
                del request.session[session_md5_key]
                raise ValidationError(
                    _(
                        "You have submitted the same file for this problem "
                        "again. Please resubmit if you really want "
                        "to submit the same file"
                    )
                )
            else:
                request.session[session_md5_key] = md5
                request.session.save()

        return cleaned_data

    def mixins_for_admin(self):
        from oioioi.programs.admin import ProgrammingProblemAdminMixin

        return super(ProgrammingProblemController, self).mixins_for_admin() + (
            ProgrammingProblemAdminMixin,
        )

    def create_submission(
        self, request, problem_instance, form_data, judge_after_create=True, **kwargs
    ):
        submission = ProgramSubmission(
            user=form_data.get('user', request.user),
            problem_instance=problem_instance,
            kind=form_data.get(
                'kind',
                problem_instance.controller.get_default_submission_kind(
                    request, problem_instance=problem_instance
                ),
            ),
            date=request.timestamp,
        )

        file = form_data['file']
        if file is None:
            lang_exts = get_allowed_languages_dict(problem_instance)
            langs_field_name = form_field_id_for_langs(problem_instance)
            extension = lang_exts[form_data[langs_field_name]][0]
            file = ContentFile(form_data['code'], '__pasted_code.' + extension)

        submission.source_file.save(file.name, file)
        submission.save()
        if judge_after_create:
            problem_instance.controller.judge(submission)
        return submission

    def _add_langs_to_form(self, request, form, problem_instance):
        controller = problem_instance.controller

        choices = [('', '')]
        for lang in get_allowed_languages_dict(problem_instance).keys():
            compiler_name = None
            compiler = controller.get_compiler_for_language(problem_instance, lang)
            if compiler is not None:
                available_compilers = getattr(settings, 'AVAILABLE_COMPILERS', {})
                compilers_for_language = available_compilers.get(lang)
                if compilers_for_language is not None:
                    compiler_info = compilers_for_language.get(compiler)
                    if compiler_info is not None:
                        compiler_name = compiler_info.get('display_name')
            langs = get_submittable_languages()
            lang_display = langs[lang]['display_name']
            if compiler_name is not None:
                choices.append((lang, "%s (%s)" % (lang_display, compiler_name)))
            else:
                choices.append((lang, lang_display))

        field_name = form_field_id_for_langs(problem_instance)
        form.fields[field_name] = forms.ChoiceField(
            required=False,
            label=_("Programming language"),
            choices=choices,
            widget=forms.Select(attrs={'disabled': 'disabled'}),
        )
        narrow_input_field(form.fields[field_name])
        form.set_custom_field_attributes(field_name, problem_instance)

    def adjust_submission_form(self, request, form, problem_instance):
        controller = problem_instance.controller
        size_limit = controller.get_submission_size_limit(problem_instance)

        def validate_file_size(file):
            if file.size > size_limit:
                raise ValidationError(_("File size limit exceeded."))

        def validate_code_length(code):
            if len(code) > size_limit:
                raise ValidationError(_("Code length limit exceeded."))

        def validate_language(file):
            ext = get_extension(file.name)
            if ext not in get_allowed_languages_extensions(problem_instance):
                raise ValidationError(_("Unknown or not supported file extension."))

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

        form.fields['file'] = forms.FileField(
            required=False,
            widget=CancellableFileInput,
            allow_empty_file=False,
            validators=[validate_file_size, validate_language],
            label=_("File"),
            help_text=mark_safe(
                _(
                    "Language is determined by the file extension."
                    " It has to be one of: %s."
                    " You can paste the code below instead of"
                    " choosing file."
                    " <strong>Try drag-and-drop too!</strong>"
                )
                % (', '.join(get_allowed_languages_extensions(problem_instance)))
            ),
        )
        form.fields['file'].widget.attrs.update(
            {'data-languagehintsurl': reverse('get_language_hints')}
        )

        use_editor = settings.USE_ACE_EDITOR
        if problem_instance.contest is not None:
            use_editor = use_editor and problem_instance.contest.enable_editor

        code_widget = None
        if use_editor:
            default_state = False
            if not request.user.is_anonymous:
                ensure_preferences_exist_for_user(request.user)
                default_state = request.user.userpreferences.enable_editor
            receipt_types = ((False, "no editor"), (True, "editor"), )
            form.fields["toggle_editor"] = forms.ChoiceField(
                required=False,
                choices=receipt_types,
                widget=forms.CheckboxInput(),
                initial=True if default_state else False,
            )
            code_widget = AceEditorWidget(
                attrs={'rows': 10, 'class': 'monospace'},
                default_state=default_state,
            )
        else:
            code_widget = forms.widgets.Textarea(
                attrs={'rows': 10, 'class': 'monospace'}
            )

        form.fields['code'] = forms.CharField(
            required=False,
            label=_("Code"),
            validators=[validate_code_length],
            widget=code_widget
        )

        self._add_langs_to_form(request, form, problem_instance)

        if 'dropped_solution' in request.POST:
            form.fields['code'].initial = request.POST['dropped_solution']

        # guessing problem name and extension when file dragged and dropped
        if 'dropped_solution_name' in request.POST:
            # do not validate blank fields this time
            form.is_bound = False

            langs_field_name = form_field_id_for_langs(problem_instance)
            fname = request.POST['dropped_solution_name']
            if fname.count('.') == 1:
                [problem, ext] = fname.split('.', 1)
                if 'problem_instance_id' not in request.POST:
                    form.fields['problem_instance_id'].initial = parse_problem(problem)
                if langs_field_name not in request.POST:
                    form.fields[langs_field_name].initial = get_language_by_extension(
                        problem_instance, ext
                    )

        self._add_js(form, ('common/submit_view.js',))

    @staticmethod
    def _add_js(form, js):
        try:
            form._js.extend(js)
        except AttributeError:
            raise TypeError("Expected SubmissionForm")

    def render_submission(self, request, submission):
        problem_instance = submission.problem_instance
        if submission.kind == 'USER_OUTS':
            # The comment includes safe string, because it is generated
            # automatically (users can not affect it).
            # Note that we temporarily assign a safestring object, because
            # field type in model is originally a string.
            submission.programsubmission.comment = mark_safe(
                submission.programsubmission.comment
            )
        can_admin = can_admin_problem_instance(request, submission.problem_instance)

        return render_to_string(
            'programs/submission_header.html',
            request=request,
            context={
                'submission': submission_template_context(
                    request, submission.programsubmission
                ),
                'problem': get_problem_link_or_name(request, submission),
                'saved_diff_id': request.session.get('saved_diff_id'),
                'supported_extra_args': problem_instance.controller.get_supported_extra_args(
                    submission
                ),
                'can_admin': can_admin,
            },
        )

    def render_report_failure(self, request, report):
        return ProblemController.render_report(self, request, report)

    def is_admin(self, request, report):
        return can_admin_problem(request, self.problem)

    def render_report(self, request, report):
        problem_instance = report.submission.problem_instance
        if report.kind == 'FAILURE':
            return problem_instance.controller.render_report_failure(request, report)

        score_report = ScoreReport.objects.get(submission_report=report)
        compilation_report = CompilationReport.objects.get(submission_report=report)
        test_reports = (
            TestReport.objects.filter(submission_report=report)
            .select_related('userout_status')
            .order_by('test__order', 'test_group', 'test_name')
        )
        group_reports = GroupReport.objects.filter(submission_report=report)
        show_scores = any(gr.score is not None for gr in group_reports)
        group_reports = dict((g.group, g) for g in group_reports)

        picontroller = problem_instance.controller

        allow_download_out = picontroller.can_generate_user_out(request, report)
        allow_test_comments = picontroller.can_see_test_comments(request, report)
        all_outs_generated = allow_download_out

        groups = []
        for group_name, tests in itertools.groupby(
            test_reports, attrgetter('test_group')
        ):
            tests_list = list(tests)

            for test in tests_list:
                test.generate_status = picontroller._out_generate_status(request, test)
                all_outs_generated &= test.generate_status == 'OK'

            tests_records = [
                {'display_type': get_report_display_type(request, test), 'test': test}
                for test in tests_list
            ]

            groups.append({'tests': tests_records, 'report': group_reports[group_name]})

        return render_to_string(
            'programs/report.html',
            request=request,
            context={
                'report': report,
                'score_report': score_report,
                'compilation_report': compilation_report,
                'groups': groups,
                'show_scores': show_scores,
                'allow_download_out': allow_download_out,
                'allow_test_comments': allow_test_comments,
                'all_outs_generated': all_outs_generated,
                'is_admin': picontroller.is_admin(request, report),
            },
        )

    def can_generate_user_out(self, request, submission_report):
        """Determines if the current user is allowed to generate outs from
        ``submission_report``.

        Default implementations allow only problem admins.
        """
        problem = submission_report.submission.problem_instance.problem
        return can_admin_problem(request, problem)

    def can_see_source(self, request, submission):
        qs = Submission.objects.filter(id=submission.id)
        return (
            request.user.is_superuser
            or self.filter_my_visible_submissions(request, qs).exists()
        )

    def can_see_test_comments(self, request, submissionreport):
        return True

    def can_see_test(self, request, test):
        return can_admin_problem(request, self.problem)

    def can_see_checker_exe(self, request, checker):
        return can_admin_problem(request, self.problem)

    def get_visible_reports_kinds(self, request, submission):
        return ['USER_OUTS', 'INITIAL', 'NORMAL']

    def filter_visible_reports(self, request, submission, queryset):
        if is_contest_basicadmin(request) or is_contest_observer(request):
            return queryset
        return queryset.filter(
            status='ACTIVE',
            kind__in=self.get_visible_reports_kinds(request, submission),
        )

    def _out_generate_status(self, request, testreport):
        problem = testreport.test.problem_instance.problem
        try:
            if (
                can_admin_problem(request, problem)
                or testreport.userout_status.visible_for_user
            ):
                # making sure, that output really exists or is processing
                if (
                    bool(testreport.output_file)
                    or testreport.userout_status.status == '?'
                ):
                    return testreport.userout_status.status

        except UserOutGenStatus.DoesNotExist:
            if testreport.output_file:
                return 'OK'

        return None

    def get_safe_exec_mode(self):
        """Determines execution mode when `USE_UNSAFE_EXEC` is False.

        Return 'sio2jail' if you want to use SIO2Jail. Otherwise return 'cpu'.
        """
        return settings.DEFAULT_SAFE_EXECUTION_MODE

    def get_allowed_languages(self):
        """Determines which languages are allowed for submissions."""
        all_languages = get_submittable_languages()
        main_languages_only = [
            lang for lang, meta in all_languages.items() if meta['type'] == 'main'
        ]
        return main_languages_only

    def render_submission_footer(self, request, submission):
        super_footer = super(
            ProgrammingProblemController, self
        ).render_submission_footer(request, submission)
        queryset = (
            Submission.objects.filter(problem_instance__contest=request.contest)
            .filter(user=submission.user)
            .filter(problem_instance=submission.problem_instance)
            .exclude(pk=submission.pk)
            .order_by('-date')
            .select_related()
        )
        if not submission.problem_instance.contest == request.contest:
            raise SuspiciousOperation
        if not is_contest_basicadmin(request) and request.contest:
            cc = request.contest.controller
            queryset = cc.filter_my_visible_submissions(request, queryset)
        elif not request.contest and not is_contest_basicadmin(request):
            pc = submission.problem_instance.controller
            queryset = pc.filter_my_visible_submissions(request, queryset)
        show_scores = bool(queryset.filter(score__isnull=False))

        can_admin = can_admin_problem_instance(request, submission.problem_instance)

        if not queryset.exists():
            return super_footer
        return super_footer + render_to_string(
            'programs/other_submissions.html',
            request=request,
            context={
                'submissions': [
                    submission_template_context(request, s) for s in queryset
                ],
                'show_scores': show_scores,
                'can_admin': can_admin,
                'main_submission_id': submission.id,
                'submissions_on_page': getattr(settings, 'SUBMISSIONS_ON_PAGE', 15),
            },
        )

    def get_allowed_languages_for_problem(self, problem):
        allowed_langs = list(
            ProblemAllowedLanguage.objects.filter(problem=problem).values_list(
                'language', flat=True
            )
        )
        if not allowed_langs:
            return problem.controller.get_allowed_languages()
        return allowed_langs


class ProgrammingContestController(ContestController):
    description = _("Simple programming contest")

    def get_compiler_for_submission(self, submission):
        problem_instance = submission.problem_instance
        return problem_instance.problem.controller.get_compiler_for_submission(
            submission
        )

    def get_compiler_for_language(self, problem_instance, language):
        contest = problem_instance.contest
        problem = problem_instance.problem
        contest_compiler_qs = ContestCompiler.objects.filter(
            contest__exact=contest, language__exact=language
        )
        if contest_compiler_qs.exists():
            return contest_compiler_qs.first().compiler
        else:
            return problem.controller.get_compiler_for_language(
                problem_instance, language
            )

    def _map_report_to_submission_status(
        self, status, problem_instance, kind='INITIAL'
    ):
        return problem_instance.problem.controller._map_report_to_submission_status(
            status, problem_instance, kind
        )

    def get_compilation_result_size_limit(self, submission):
        return submission.problem_instance.problem.controller.get_compilation_result_size_limit(
            submission
        )

    def fill_evaluation_environ(self, environ, submission):
        problem = submission.problem_instance.problem
        problem.controller.fill_evaluation_environ(environ, submission)
        self.fill_evaluation_environ_post_problem(environ, submission)

    def fill_evaluation_environ_post_problem(self, environ, submission):
        """Run after ProblemController.fill_evaluation_environ."""
        if 'INITIAL' in environ['report_kinds']:
            add_before_placeholder(
                environ,
                'after_initial_tests',
                (
                    'update_report_statuses',
                    'oioioi.contests.handlers.update_report_statuses',
                ),
            )
            add_before_placeholder(
                environ,
                'after_initial_tests',
                (
                    'update_submission_score',
                    'oioioi.contests.handlers.update_submission_score',
                ),
            )

    def get_submission_size_limit(self, problem_instance):
        return problem_instance.problem.controller.get_submission_size_limit(
            problem_instance
        )

    def check_repeated_submission(self, request, problem_instance, form):
        return (
            not is_contest_basicadmin(request)
            and form.kind == 'NORMAL'
            and getattr(settings, 'WARN_ABOUT_REPEATED_SUBMISSION', False)
        )

    def update_report_statuses(self, submission, queryset):
        """Updates statuses of reports for the newly judged submission.

        Usually this involves looking at reports and deciding which should
        be ``ACTIVE`` and which should be ``SUPERSEDED``.

        :param submission: an instance of
                           :class:`oioioi.contests.models.Submission`
        :param queryset: a queryset returning reports for the submission
        """
        controller = submission.problem_instance.controller
        controller._activate_newest_report(
            submission, queryset, kind=['NORMAL', 'FAILURE']
        )
        controller._activate_newest_report(submission, queryset, kind=['INITIAL'])
        controller._activate_newest_report(submission, queryset, kind=['USER_OUTS'])

    def can_see_submission_status(self, request, submission):
        """Statuses are taken from initial tests which are always public."""
        return True

    def can_see_test(self, request, test):
        return can_admin_problem_instance(request, test.problem_instance)

    def can_see_checker_exe(self, request, checker):
        return can_admin_problem_instance(request, checker.problem_instance)

    def get_visible_reports_kinds(self, request, submission):
        if self.results_visible(request, submission):
            return ['USER_OUTS', 'INITIAL', 'NORMAL']
        else:
            return ['USER_OUTS', 'INITIAL']

    def filter_visible_reports(self, request, submission, queryset):
        if is_contest_basicadmin(request) or is_contest_observer(request):
            return queryset
        return queryset.filter(
            status='ACTIVE',
            kind__in=self.get_visible_reports_kinds(request, submission),
        )

    def filter_my_visible_submissions(self, request, queryset, filter_user=True):
        if not is_contest_basicadmin(request):
            queryset = queryset.exclude(kind='USER_OUTS')
        return super(ProgrammingContestController, self).filter_my_visible_submissions(
            request, queryset, filter_user
        )

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
        if is_contest_basicadmin(request) or is_contest_observer(request):
            return True
        if not has_report_actions_config(submission.problem_instance.problem):
            return False
        config = submission.problem_instance.problem.report_actions_config

        return (
            config.can_user_generate_outs
            and submission.user == request.user
            and self.can_see_problem(request, submission.problem_instance)
            and self.filter_visible_reports(
                request,
                submission,
                SubmissionReport.objects.filter(id=submission_report.id),
            ).exists()
        )

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
        if is_contest_basicadmin(request):
            return filter_model_submissions(queryset)
        return self.filter_my_visible_submissions(request, queryset)

    def can_see_source(self, request, submission):
        """Check if submission's source should be visible.
        :type submission: oioioi.contest.Submission

        Consider using filter_visible_sources instead, especially for batch
        queries.
        """
        qs = Submission.objects.filter(id=submission.id)
        if not (
            is_contest_admin(request) or is_contest_observer(request)
        ) and is_model_submission(submission):
            return False
        return self.filter_visible_sources(request, qs).exists()

    def render_submission(self, request, submission):
        problem = submission.problem_instance.problem
        return problem.controller.render_submission(request, submission)

    def _out_generate_status(self, request, testreport):
        try:
            if (
                is_contest_basicadmin(request)
                or testreport.userout_status.visible_for_user
            ):
                # making sure, that output really exists or is processing
                if (
                    bool(testreport.output_file)
                    or testreport.userout_status.status == '?'
                ):
                    return testreport.userout_status.status

        except UserOutGenStatus.DoesNotExist:
            if testreport.output_file:
                return 'OK'

        return None

    def can_see_test_comments(self, request, submissionreport):
        return submissionreport.submission.problem_instance.problem.controller.can_see_test_comments(
            request, submissionreport
        )

    def render_report_failure(self, request, report):
        return ContestController.render_report(self, request, report)

    def is_admin(self, request, report):
        return is_contest_basicadmin(request)

    def render_report(self, request, report):
        return report.submission.problem_instance.problem.controller.render_report(
            request, report
        )

    def render_submission_footer(self, request, submission):
        return super(ProgrammingContestController, self).render_submission_footer(
            request, submission
        )

    def valid_kinds_for_submission(self, submission):
        if ModelProgramSubmission.objects.filter(id=submission.id).exists():
            return [submission.kind]

        if submission.kind == 'USER_OUTS':
            return ['USER_OUTS']

        return super(ProgrammingContestController, self).valid_kinds_for_submission(
            submission
        )

    def get_safe_exec_mode(self):
        """Determines execution mode when `USE_UNSAFE_EXEC` is False.

        Return 'sio2jail' if you want to use SIO2Jail. Otherwise return 'cpu'.
        """
        if (
            hasattr(self.contest, 'programs_config')
            and self.contest.programs_config.execution_mode != 'AUTO'
        ):
            return self.contest.programs_config.execution_mode
        else:
            return self.get_default_safe_exec_mode()

    def get_default_safe_exec_mode(self):
        return settings.DEFAULT_SAFE_EXECUTION_MODE

    def get_allowed_languages(self):
        """Determines which languages are allowed for submissions."""
        return get_submittable_languages().keys()
