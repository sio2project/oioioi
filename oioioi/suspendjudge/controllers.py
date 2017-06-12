from oioioi.evalmgr import add_before_recipe_entry, add_before_placeholder
from oioioi.programs.controllers import ProgrammingContestController


class SuspendJudgeContestControllerMixin(object):
    """ContestController mixin that adds suspendjudge app's handlers to environ
       recipe.
    """

    def finalize_evaluation_environment(self, environ):
        super(SuspendJudgeContestControllerMixin, self) \
                .finalize_evaluation_environment(environ)
        try:
            add_before_recipe_entry(environ, 'compile', (
                'check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state',
                dict(suspend_init_tests=True)))
        except IndexError:
            pass

        try:
            add_before_placeholder(environ, 'before_final_tests', (
                'check_problem_instance_state',
                'oioioi.suspendjudge.handlers.check_problem_instance_state'))
        except IndexError:
            pass


ProgrammingContestController.mix_in(SuspendJudgeContestControllerMixin)
