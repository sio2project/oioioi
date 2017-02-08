from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oioioi.evalmgr import recipe_placeholder
from oioioi.programs.controllers import ProgrammingProblemController, \
        ProgrammingContestController
from oioioi.zeus.models import ZeusProblemData
from oioioi.zeus.utils import is_zeus_problem


class ZeusProblemController(ProgrammingProblemController):
    description = _("Zeus programming problem")

    def generate_base_environ(self, environ, submission, **kwargs):
        self.generate_initial_evaluation_environ(environ, submission)
        environ['recipe'] = []
        zeus_problem, _created = ZeusProblemData.objects \
            .get_or_create(problem=self.problem)
        environ['zeus_id'] = zeus_problem.zeus_id
        environ['zeus_problem_id'] = zeus_problem.zeus_problem_id
        environ.setdefault('evalmgr_extra_args', {})['queue'] = 'evalmgr-zeus'

    def generate_recipe(self, kinds):
        recipe_body = [
        ]

        # NOTE this will do nothing if the contest type is ACM
        # and kinds=['FULL']
        if 'INITIAL' in kinds:
            recipe_body.extend(
                [
                    recipe_placeholder('before_initial_tests'),
                    ('initial_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='INITIAL')),
                    recipe_placeholder('before_initial_async'),
                    ('mark_submission_waiting',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='WAITING')),
                    ('initial_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='INITIAL')),
                    ('dump',
                        'oioioi.evalmgr.handlers.dump_env',
                        dict(message="AFTER INITIAL")),


                    # current job ends here, the following will be asynchronous
                    ('mark_submission_in_progress',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='PROGRESS-RESUMED')),
                    ('initial_import_results',
                        'oioioi.zeus.handlers.import_results'),
                    ('initial_update_tests_set',
                        'oioioi.zeus.handlers.update_problem_tests_set',
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
                    ('mark_submission_waiting',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='WAITING')),
                    ('final_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='NORMAL')),
                    ('dump',
                        'oioioi.evalmgr.handlers.dump_env',
                        dict(message="AFTER NORMAL")),

                    # current job ends here, the following will be asynchronous
                    ('mark_submission_in_progress',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='PROGRESS-RESUMED')),
                    ('final_import_results',
                        'oioioi.zeus.handlers.import_results'),
                    ('final_update_tests_set',
                        'oioioi.zeus.handlers.update_problem_tests_set',
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
                    ('mark_submission_waiting',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='WAITING')),

                    # current job ends here, the following will be asynchronous
                    ('mark_submission_in_progress',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='PROGRESS-RESUMED')),
                    ('final_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='NORMAL')),
                    recipe_placeholder('before_final_async'),
                    ('mark_submission_waiting',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='WAITING')),
                    ('final_save_async_job',
                        'oioioi.zeus.handlers.save_env',
                        dict(kind='NORMAL')),

                    # another asynchronous part
                    ('mark_submission_in_progress',
                        'oioioi.submitsqueue.handlers.mark_submission_state',
                        dict(state='PROGRESS-RESUMED')),
                    ('import_results',
                        'oioioi.zeus.handlers.import_results'),
                    ('initial_update_tests_set',
                        'oioioi.zeus.handlers.update_problem_tests_set',
                        dict(kind='EXAMPLE')),
                    #('final_import_tests', TODO this does nothing, remove it
                    #    'oioioi.zeus.handlers.import_results',
                    #    dict(kind='NORMAL')),
                    ('final_update_tests_set',
                        'oioioi.zeus.handlers.update_problem_tests_set',
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

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        self.generate_base_environ(environ, submission, **kwargs)

        environ['recipe'].extend(self.generate_recipe(environ['report_kinds']))

        environ.setdefault('group_scorer',
            'oioioi.programs.utils.min_group_scorer')
        environ.setdefault('score_aggregator',
            'oioioi.programs.utils.sum_score_aggregator')

    def filter_allowed_languages_dict(self, languages, problem_instance):
        return {k: languages[k] for k in languages
                if k in settings.ZEUS_ALLOWED_LANGUAGES}


class ZeusContestControllerMixin(object):
    allow_to_late_mixins = True

    def use_spliteval(self, submission):
        if is_zeus_problem(submission.problem_instance.problem):
            return False
        return super(ZeusContestControllerMixin, self) \
                .use_spliteval(submission)


ProgrammingContestController.mix_in(ZeusContestControllerMixin)
