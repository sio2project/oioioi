from oioioi.contests.models import Contest, ProblemInstance, Round
from oioioi.problems.models import Problem
from oioioi.problems.utils import get_new_problem_instance, update_tests_from_main_pi


def update_problem_instance(env):
    """Updates :class:`~oioioi.contests.models.ProblemInstance` for the
    processed :class:`~oioioi.problems.models.Problem`
    (if contest and round are given creates an
    :class:`~oioioi.contests.models.ProblemInstance` which is a copy of
    problem.main_problem_instance and assigns it to Contest and Round.

    Used ``env`` keys:
      ``problem_id``: id of the processed
      :class:`~oioioi.problems.models.Problem`

      ``contest_id``: id of the :class:`~oioioi.contests.models.Contest` the
      problem instance should be attached to.

      ``round_id``: (Optional) id of the
      :class:`~oioioi.contests.models.Round` the problem instance should
      be attached to.

      ``is_reupload``: set on True when problem is being reuploaded
    """
    problem = Problem.objects.get(id=env['problem_id'])
    if env.get('contest_id', None):
        pi = ProblemInstance.objects.filter(
            contest__id=env['contest_id'], problem=problem
        ).first()
        if not pi:
            contest = Contest.objects.get(id=env['contest_id'])
            pi = get_new_problem_instance(problem, contest)
            if env.get('round_id', None) and not pi.round:
                pi.round = Round.objects.get(id=env['round_id'])
            pi.save()
        env['problem_instance_id'] = pi.id
    if env['is_reupload']:
        update_all_probleminstances_after_reupload(problem)

    return env


def update_all_probleminstances_after_reupload(problem):
    """Updates test_set for every problem_instance assigned to Problem.
    to main_problem_instance.test_set
    """
    for pi in problem.probleminstance_set.filter(contest__isnull=False):
        update_tests_from_main_pi(pi)
        pi.needs_rejudge = True
        pi.save()
