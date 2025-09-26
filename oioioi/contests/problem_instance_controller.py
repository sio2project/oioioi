class ProblemInstanceController:
    """
    ``ProblemInstanceController`` decides whether to call problem
    controller or contest controller. Problem controller will be chosen
    if the problem instance is not attached to any contest (eg. for
    ``main_problem_instance``).

    Outside functions which want to call one of the above controllers
    and it is not clear that contest controller exists, should call
    ``ProblemInstanceController``, example::

        problem_instance.contest.controller.get_submissions_limit()  # WRONG
        problem_instance.controller.get_submissions_limit()  # GOOD

    From its functions the contest controller can call the problem
    controller, but the problem controller should not call the contest
    controller.

    For visuals::

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
            assert hasattr(contest.controller, name) or not hasattr(problem.controller, name)
            return getattr(contest.controller, name)
        return getattr(problem.controller, name)
