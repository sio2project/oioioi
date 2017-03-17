from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oioioi.evalmgr import recipe_placeholder
from oioioi.programs.controllers import ProgrammingProblemController
from oioioi.zeus.models import ZeusProblemData


class ZeusProblemController(ProgrammingProblemController):
    description = _("Zeus programming problem")

    def generate_base_environ(self, environ, submission, **kwargs):
        self.generate_initial_evaluation_environ(environ, submission)
        zeus_problem, _created = ZeusProblemData.objects \
            .get_or_create(problem=self.problem)
        environ['zeus_id'] = zeus_problem.zeus_id
        environ['zeus_problem_id'] = zeus_problem.zeus_problem_id
        environ.setdefault('evalmgr_extra_args', {})['queue'] = 'evalmgr-zeus'

    def generate_recipe(self, kinds):
        recipe_body = []

        # NOTE this will do nothing if the contest type is ACM
        # and kinds=['FULL']
        if 'INITIAL' in kinds:
            recipe_body.extend(
                [
                    recipe_placeholder('before_initial_tests'),
                    ('initial_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='INITIAL')),

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
                    recipe_placeholder('before_initial_tests'),
                    ('initial_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='INITIAL')),

                    recipe_placeholder('before_final_tests'),
                    ('final_submit_job',
                        'oioioi.zeus.handlers.submit_job',
                        dict(kind='NORMAL')),

                    ('import_results',
                        'oioioi.zeus.handlers.import_results'),
                    ('initial_update_tests_set',
                        'oioioi.zeus.handlers.update_problem_tests_set',
                        dict(kind='EXAMPLE')),
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

        environ.setdefault('recipe', []).extend(
                self.generate_recipe(environ['report_kinds']))

        environ.setdefault('group_scorer',
            'oioioi.programs.utils.min_group_scorer')
        environ.setdefault('score_aggregator',
            'oioioi.programs.utils.sum_score_aggregator')

    def filter_allowed_languages_dict(self, languages, problem_instance):
        return {k: languages[k] for k in languages
                if k in settings.ZEUS_ALLOWED_LANGUAGES}
