class ProblemInstanceController(object):
    """
        ProblemInstanceController decides whether to call ProblemController
        or ContestController. ProblemController will be chosen if and only if
        contest does not exist (eg. for main_problem_instance).

        Every outside functions which want to call one of above controllers
        and it is not clear that ContestController exists,
        should call ProblemInstanceController, example:
            problem_instace.contest.controller.get_submissions_limit() - WRONG
            problem_instace.controller.get_submissions_limit() - GOOD

        In its functions ContestController can call ProblemController,
        but ProblemController should not call ContestController

        For visuals:
            Call, for example *.get_submissions_limit()
                            |
                            V
               ProblemInstanceController
                 |                    |
                 V                    V
         ContestController  -->  ProblemController
    """
    def __init__(self, problem_instance):
        self.problem_instance = problem_instance

    def __getattr__(self, name):
        problem = self.problem_instance.problem
        contest = self.problem_instance.contest

        if contest is not None:
            assert hasattr(contest.controller, name) \
                or not hasattr(problem.controller, name)
            return getattr(contest.controller, name)
        return getattr(problem.controller, name)
