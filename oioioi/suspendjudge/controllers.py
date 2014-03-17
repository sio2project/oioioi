from oioioi.evalmgr import add_before_placeholder, add_after_recipe_entry
from oioioi.programs.controllers import ProgrammingContestController


class SuspendJudgeContestControllerMixin(object):
    def finalize_evaluation_environment(self, environ):
        super(SuspendJudgeContestControllerMixin, self) \
                .finalize_evaluation_environment(environ)

        add_after_recipe_entry(environ, 'mark_submission_in_progress', (
            'check_problem_instance_state',
            'oioioi.suspendjudge.handlers.check_problem_instance_state',
            dict(suspend_init_tests=True)))

        try:
            add_before_placeholder(environ, 'before_final_tests', (
                'check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state'))
        except IndexError:
            pass


ProgrammingContestController.mix_in(SuspendJudgeContestControllerMixin)
