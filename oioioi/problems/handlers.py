from oioioi.contests.models import Contest, ProblemInstance, Round
from oioioi.problems.models import Problem


def update_main_problem_instance(env):
    """Updates :class:`~oioioi.contests.models.ProblemInstance` for the
       processed :class:`~oioioi.problems.models.Problem`
       (assigns correct contest and round).

       Used ``env`` keys:
         ``problem_id``: id of the processed
         :class:`~oioioi.problems.models.Problem`

         ``contest_id``: id of the :class:`~oioioi.contests.models.Contest` the
         problem instance should be attached to.

         ``round_id``: (Optional) id of the
         :class:`~oioioi.contests.models.Round` the problem instance should
         be attached to.
    """
    problem = Problem.objects.get(id=env['problem_id'])
    if env.get('contest_id', None):
        pi = problem.main_problem_instance
        pi.contest = Contest.objects.get(id=env['contest_id'])
        if env.get('round_id', None) and not pi.round:
            pi.round = Round.objects.get(id=env['round_id'])
        pi.save()
        env['problem_instance_id'] = pi.id
    return env
