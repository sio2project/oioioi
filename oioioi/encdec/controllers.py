import itertools
from operator import attrgetter  # pylint: disable=E0611

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from oioioi.contests.controllers import submission_template_context
from oioioi.encdec.models import EncdecChannel, EncdecChecker, EncdecTestReport
from oioioi.evalmgr.tasks import (
    add_before_placeholder,
    extend_after_placeholder,
    recipe_placeholder,
)
from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.problems.utils import can_admin_problem, can_admin_problem_instance
from oioioi.programs.controllers import ProgrammingProblemController
from oioioi.programs.utils import (
    get_extension,
    get_problem_link_or_name,
)
from oioioi.contests.models import ScoreReport, SubmissionReport
from oioioi.programs.models import CompilationReport, GroupReport


def get_report_display_type(request, status, score, max_score):
    if status == 'INI_OK' or status == 'OK':
        try:
            if score is None or max_score is None:
                display_type = status

            elif max_score.to_int() == 0:
                display_type = status

            else:
                score_percentage = (
                    float(score.to_int()) / max_score.to_int()
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
            display_type = status

    else:
        display_type = status

    return display_type

class EncdecProblemController(ProgrammingProblemController):
    description = _("Encoder-decoder programming problem")

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

    def generate_recipe(self, kinds):
        recipe_body = [('collect_tests', 'oioioi.encdec.handlers.collect_tests')]

        if 'INITIAL' in kinds:
            recipe_body.extend(
                [
                    (
                        'initial_run_encoder',
                        'oioioi.encdec.handlers.run_encoder',
                        dict(kind='EXAMPLE'),
                    ),
                    ('initial_run_encoder_end', 'oioioi.encdec.handlers.run_encoder_end'),
                    ('initial_grade_encoder', 'oioioi.encdec.handlers.grade_encoder'),
                    (
                        'initial_run_decoder',
                        'oioioi.encdec.handlers.run_decoder',
                        dict(kind='EXAMPLE'),
                    ),
                    ('initial_run_decoder_end', 'oioioi.encdec.handlers.run_decoder_end'),
                    ('initial_grade_decoder', 'oioioi.encdec.handlers.grade_decoder'),
                    ('initial_grade_groups', 'oioioi.encdec.handlers.grade_groups'),
                    (
                        'initial_grade_submission',
                        'oioioi.encdec.handlers.grade_submission',
                        dict(kind='EXAMPLE'),
                    ),
                    (
                        'initial_make_report',
                        'oioioi.encdec.handlers.make_report',
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
                        'oioioi.encdec.handlers.run_tests',
                        dict(kind=None),
                    ),
                    ('userout_run_tests', 'oioioi.encdec.handlers.run_tests_end'),
                    ('userout_grade_tests', 'oioioi.encdec.handlers.grade_tests'),
                    ('userout_grade_groups', 'oioioi.encdec.handlers.grade_groups'),
                    (
                        'userout_grade_submission',
                        'oioioi.encdec.handlers.grade_submission',
                        dict(kind=None),
                    ),
                    (
                        'userout_make_report',
                        'oioioi.encdec.handlers.make_report',
                        dict(kind='USER_OUTS', save_scores=False),
                    ),
                    (
                        'userout_fill_outfile_in_existing_test_reports',
                        'oioioi.encdec.handlers.'
                        'fill_outfile_in_existing_test_reports',
                    ),
                    (
                        'userout_insert_existing_submission_link',
                        'oioioi.encdec.handlers.' 'insert_existing_submission_link',
                    ),
                ]
            )

        if 'NORMAL' in kinds or 'HIDDEN' in kinds or 'FULL' in kinds:
            recipe_body.append(recipe_placeholder('before_final_tests'))

        if 'NORMAL' in kinds:
            recipe_body.extend(
                [
                    (
                        'final_run_encoder',
                        'oioioi.encdec.handlers.run_encoder',
                        dict(kind='NORMAL'),
                    ),
                    ('final_run_encoder_end', 'oioioi.encdec.handlers.run_encoder_end'),
                    ('final_grade_encoder', 'oioioi.encdec.handlers.grade_encoder'),
                    (
                        'final_run_decoder',
                        'oioioi.encdec.handlers.run_decoder',
                        dict(kind='NORMAL'),
                    ),
                    ('final_run_decoder_end', 'oioioi.encdec.handlers.run_decoder_end'),
                    ('final_grade_decoder', 'oioioi.encdec.handlers.grade_decoder'),
                    ('final_grade_groups', 'oioioi.encdec.handlers.grade_groups'),
                    (
                        'final_grade_submission',
                        'oioioi.encdec.handlers.grade_submission',
                    ),
                    ('final_make_report', 'oioioi.encdec.handlers.make_report'),
                    recipe_placeholder('after_final_tests'),
                ]
            )

        if 'HIDDEN' in kinds:
            recipe_body.extend(
                [
                    ('hidden_run_encoder', 'oioioi.encdec.handlers.run_encoder'),
                    ('hidden_run_encoder_end', 'oioioi.encdec.handlers.run_encoder_end'),
                    ('hidden_grade_encoder', 'oioioi.encdec.handlers.grade_encoder'),
                    ('hidden_run_decoder', 'oioioi.encdec.handlers.run_decoder'),
                    ('hidden_run_decoder_end', 'oioioi.encdec.handlers.run_decoder_end'),
                    ('hidden_grade_decoder', 'oioioi.encdec.handlers.grade_decoder'),
                    ('hidden_grade_groups', 'oioioi.encdec.handlers.grade_groups'),
                    (
                        'hidden_grade_submission',
                        'oioioi.encdec.handlers.grade_submission',
                        dict(kind=None),
                    ),
                    (
                        'hidden_make_report',
                        'oioioi.encdec.handlers.make_report',
                        dict(kind='HIDDEN'),
                    ),
                    recipe_placeholder('after_all_tests'),
                ]
            )

        if 'FULL' in kinds:
            recipe_body.extend(
                [
                    ('full_run_encoder', 'oioioi.encdec.handlers.run_encoder'),
                    ('full_run_encoder', 'oioioi.encdec.handlers.run_encoder_end'),
                    ('full_grade_encoder', 'oioioi.encdec.handlers.grade_encoder'),
                    ('full_run_decoder', 'oioioi.encdec.handlers.run_decoder'),
                    ('full_run_decoder', 'oioioi.encdec.handlers.run_decoder_end'),
                    ('full_grade_decoder', 'oioioi.encdec.handlers.grade_decoder'),
                    ('full_grade_groups', 'oioioi.encdec.handlers.grade_groups'),
                    (
                        'full_grade_submission',
                        'oioioi.encdec.handlers.grade_submission',
                        dict(kind=None),
                    ),
                    (
                        'full_make_report',
                        'oioioi.encdec.handlers.make_report',
                        dict(kind='FULL'),
                    ),
                    recipe_placeholder('after_full_tests'),
                ]
            )

        return recipe_body

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

        channel = EncdecChannel.objects.get(problem=self.problem).exe_file
        checker = EncdecChecker.objects.get(problem=self.problem).exe_file

        environ['channel'] = django_to_filetracker_path(channel)
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
            'encdec/submission_header.html',
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

    def render_report(self, request, report):
        problem_instance = report.submission.problem_instance
        if report.kind == 'FAILURE':
            return problem_instance.controller.render_report_failure(request, report)

        score_report = ScoreReport.objects.get(submission_report=report)
        compilation_report = CompilationReport.objects.get(submission_report=report)
        test_reports = (
            EncdecTestReport.objects.filter(submission_report=report)
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
                {'encoder_display_type': get_report_display_type(request, test.encoder_status, test.score, test.max_score),
                 'decoder_display_type': get_report_display_type(request, test.decoder_status, test.score, test.max_score),
                 'test': test}
                for test in tests_list
            ]

            groups.append({'tests': tests_records, 'report': group_reports[group_name]})

        return render_to_string(
            'encdec/report.html',
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
