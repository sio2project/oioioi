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

from oioioi.contests.utils import is_contest_admin, is_contest_observer
from oioioi.problems.controllers import ProblemController
from oioioi.contests.controllers import ContestController, \
        submission_template_context
from oioioi.contests.models import SubmissionReport, ScoreReport
from oioioi.programs.models import ProgramSubmission, OutputChecker, \
        CompilationReport, TestReport, GroupReport, ModelProgramSubmission, \
        Submission, ReportActionsConfig, UserOutGenStatus
from oioioi.programs.utils import has_report_actions_config
from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.evalmgr import recipe_placeholder, add_before_placeholder, \
        extend_after_placeholder
from oioioi.base.utils.user_selection import UserSelectionField

logger = logging.getLogger(__name__)


class ProgrammingProblemController(ProblemController):
    description = _("Simple programming problem")

    def generate_base_environ(self, environ, **kwargs):
        environ['recipe'] = [
                ('compile',
                    'oioioi.programs.handlers.compile'),

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
                    ('userout_grade_tests',
                        'oioioi.programs.handlers.grade_tests'),
                    ('userout_grade_groups',
                        'oioioi.programs.handlers.grade_groups'),
                    ('userout_grade_submission',
                        'oioioi.programs.handlers.grade_submission',
                        dict(kind=None)),
                    ('userout_make_report',
                        'oioioi.programs.handlers.make_report',
                        dict(kind='USER_OUTS', scores=False)),
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

    def fill_evaluation_environ(self, environ, **kwargs):
        self.generate_base_environ(environ, **kwargs)

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

    def filter_allowed_languages_dict(self, languages):
        return languages

    def mixins_for_admin(self):
        from oioioi.programs.admin import ProgrammingProblemAdminMixin
        return super(ProgrammingProblemController, self).mixins_for_admin() \
                + (ProgrammingProblemAdminMixin,)


class ProgrammingContestController(ContestController):
    description = _("Simple programming contest")

    def get_compilation_result_size_limit(self):
        return 10 * 1024 * 1024

    def _get_language(self, source_file):
        return os.path.splitext(source_file.name)[1][1:]

    def use_spliteval(self, submission):
        return True

    def fill_evaluation_environ(self, environ, submission):
        submission = submission.programsubmission
        environ['source_file'] = \
            django_to_filetracker_path(submission.source_file)
        environ['language'] = self._get_language(submission.source_file)
        environ['compilation_result_size_limit'] = \
            self.get_compilation_result_size_limit()

        super(ProgrammingContestController,
                self).fill_evaluation_environ(environ, submission)

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

    def get_submission_size_limit(self):
        return 102400  # in bytes

    def get_allowed_languages_dict(self):
        return getattr(settings, 'SUBMITTABLE_EXTENSIONS', {})

    def get_allowed_languages(self):
        return self.get_allowed_languages_dict().keys()

    def get_allowed_extensions(self):
        lang_exts = self.get_allowed_languages_dict().values()
        return [ext for lang in lang_exts for ext in lang]

    def parse_language_by_extension(self, ext):
        for lang, extension_list in self.get_allowed_languages_dict().items():
            if ext in extension_list:
                return lang
        return None

    def adjust_submission_form(self, request, form):
        super(ProgrammingContestController, self) \
                  .adjust_submission_form(request, form)
        size_limit = self.get_submission_size_limit()

        def validate_file_size(file):
            if file.size > size_limit:
                raise ValidationError(_("File size limit exceeded."))

        def validate_language(file):
            ext = self._get_language(file)
            if ext not in self.get_allowed_extensions():
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
                help_text=_("Language is determined by the file extension."
                            " The following are recognized: %s, but allowed"
                            " languages may vary. You can paste the code"
                            " below instead of choosing file."
                            " You can also submit your solution on any"
                            " other page by file drag'n'drop!"
                ) % (', '.join(self.get_allowed_extensions()))
        )
        form.fields['code'] = forms.CharField(required=False,
                label=_("Code"),
                widget=forms.widgets.Textarea(attrs={'rows': 10,
                    'class': 'monospace input-xxxlarge'})
        )

        choices = [('', '')]
        choices += [(lang, lang) for lang in self.get_allowed_languages()]
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
                            self.parse_language_by_extension(ext)

        if is_contest_admin(request):
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
                        self.registration_controller() \
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
            cleaned_data['prog_lang'] = self.parse_language_by_extension(ext)

        if not cleaned_data['prog_lang']:
            if is_code_pasted:
                raise ValidationError(_("You have to choose programming "
                                        "language."))
            else:
                raise ValidationError(_("Unrecognized file extension."))

        pc = cleaned_data['problem_instance'].problem.controller
        langs = pc.filter_allowed_languages_dict(
                self.get_allowed_languages_dict())
        if cleaned_data['prog_lang'] not in langs.keys():
            raise ValidationError(_("This language is not allowed for selected"
                                    " problem."))

        if is_file_chosen:
            code = cleaned_data['file'].read()
        else:
            code = cleaned_data['code'].encode('utf-8')

        if not is_contest_admin(request) and form.kind == 'NORMAL' and \
                getattr(settings, 'WARN_ABOUT_REPEATED_SUBMISSION', False):
            lines = iter(code.splitlines())
            md5 = hashlib.md5()
            for line in lines:
                md5.update(line)
            md5 = md5.hexdigest()

            if 'programs_last_md5' in request.session and \
                    md5 == request.session['programs_last_md5']:
                del request.session['programs_last_md5']
                raise ValidationError(
                    _("You have submitted the same file again."
                    " Please resubmit if you really want "
                    " to submit the same file"))
            else:
                request.session['programs_last_md5'] = md5
                request.session.save()

        return cleaned_data

    def create_submission(self, request, problem_instance, form_data,
                    judge_after_create=True, **kwargs):
        submission = ProgramSubmission(
                user=form_data.get('user', request.user),
                problem_instance=problem_instance,
                kind=form_data.get('kind',
                        self.get_default_submission_kind(request)),
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
            self.judge(submission)
        return submission

    def update_report_statuses(self, submission, queryset):
        self._activate_newest_report(submission, queryset,
                kind=['NORMAL', 'FAILURE'])
        self._activate_newest_report(submission, queryset,
                kind=['INITIAL'])
        self._activate_newest_report(submission, queryset,
                kind=['USER_OUTS'])

    def can_see_submission_status(self, request, submission):
        """Statuses are taken from initial tests which are always public."""
        return True

    def _map_report_to_submission_status(self, status, kind='INITIAL'):
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
            submission.status = self._map_report_to_submission_status(
                    score_report.status, kind=kind_for_status)
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

        return config.can_user_generate_outs and \
                submission.user == request.user and \
                self.can_see_problem(request, submission.problem_instance) and \
                self.filter_visible_reports(request, submission,
                    SubmissionReport.objects.filter(id=submission_report.id)) \
                    .exists()

    def can_see_source(self, request, submission):
        """Determines if the current user is allowed to see source
           of ``submission``.

           This usually involves cross-user privileges, like publicizing
           sources.
           Default implementations delegates to
           :meth:`~ContestController.filter_my_visible_submissions`, except for
           admins and observers, which get full access.
        """
        if is_contest_admin(request) or is_contest_observer(request):
            return True
        queryset = Submission.objects.filter(id=submission.id)
        return self.filter_my_visible_submissions(request, queryset).exists()

    def render_submission(self, request, submission):
        if submission.kind == 'USER_OUTS':
            # safe html href in comment
            submission.programsubmission.comment = \
                mark_safe(submission.programsubmission.comment)

        return render_to_string('programs/submission_header.html',
                context_instance=RequestContext(request,
                    {'submission': submission_template_context(request,
                        submission.programsubmission),
                    'saved_diff_id': request.session.get('saved_diff_id'),
                    'supported_extra_args':
                        self.get_supported_extra_args(submission)}))

    def _out_generate_status(self, request, testreport):
            try:
                download_control = UserOutGenStatus.objects.get(
                                                        testreport=testreport)

                if is_contest_admin(request) or \
                        download_control.visible_for_user:
                    # making sure, that output really exists or is processing
                    if bool(testreport.output_file) or \
                            download_control.status == '?':
                        return download_control.status

            except UserOutGenStatus.DoesNotExist:
                if bool(testreport.output_file):
                    return 'OK'

            return None

    def render_report(self, request, report):
        if report.kind == 'FAILURE':
            return ContestController.render_report(self, request,
                    report)

        score_report = ScoreReport.objects.get(submission_report=report)
        compilation_report = \
                CompilationReport.objects.get(submission_report=report)
        test_reports = TestReport.objects.filter(submission_report=report) \
                .order_by('test__order', 'test_group', 'test_name')
        group_reports = GroupReport.objects.filter(submission_report=report)
        show_scores = any(gr.score is not None for gr in group_reports)
        group_reports = dict((g.group, g) for g in group_reports)

        show_actions_col = False
        allow_download_out = self.can_generate_user_out(request, report)
        all_outs_generated = allow_download_out

        groups = []
        for group_name, tests in itertools.groupby(test_reports,
                attrgetter('test_group')):
            tests_list = list(tests)
            groups.append({'tests': tests_list,
                'report': group_reports[group_name]})

            for test in tests_list:
                test.generate_status = self._out_generate_status(request, test)
                all_outs_generated &= (test.generate_status == 'OK')
                show_actions_col |= (test.generate_status is not None)

        show_actions_col &= allow_download_out

        return render_to_string('programs/report.html',
                context_instance=RequestContext(request,
                    {'report': report, 'score_report': score_report,
                        'compilation_report': compilation_report,
                        'groups': groups, 'show_scores': show_scores,
                        'show_actions': show_actions_col,
                        'allow_download_out': allow_download_out,
                        'all_outs_generated': all_outs_generated}))

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
