from oioioi.problems.models import Problem
from oioioi.gamification.models import ProblemDifficulty
from oioioi.sinolpack.models import ExtraConfig


class DIFFICULTY(object):
    """Problem difficulty enum, returned by get_problem_difficulty"""
    TRIVIAL = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    IMPOSSIBLE = 5


def get_problem_difficulty(problem):
    """Returns None if no difficulty was set, or a number (1-5) which
       can be compared using DIFFICULTY object"""
    try:
        return ProblemDifficulty.objects.get(problem=problem).difficulty
    except ProblemDifficulty.DoesNotExist:
        return None


def get_problems_by_difficulty(difficulty):
    """Returns a queryset of all problems that have the desired difficulty"""
    return Problem.objects.filter(problemdifficulty__difficulty=difficulty)


def parse_old_problems():
    """Finds all problems that don't have difficulty rows and create those.
       Useful when you activate gamification on old deployment and have a
       lot of old problems with no difficulty. Probably called from shell by
       user
    """
    # A temporary solution for temporary problem -> waiting for tags in problem
    # database
    empty_problems = Problem.objects.filter(
        problemdifficulty__isnull=True
    ).all()
    for problem in empty_problems:
        _update_problem_difficulty(problem)


def _update_problem_difficulty(problem):
    """Creates row with difficulty for the given problem"""
    result = None
    try:
        # We're skipping a layer of abstraction here, a hack before tags
        # are added to problem database
        config = ExtraConfig.objects.get(problem=problem)
        difficulty = config.parsed_config['difficulty']
        if isinstance(difficulty, str):
            diff_lower = difficulty.lower()
            if diff_lower == 'trivial':
                result = DIFFICULTY.TRIVIAL
            elif diff_lower == 'easy':
                result = DIFFICULTY.EASY
            elif diff_lower == 'medium':
                result = DIFFICULTY.MEDIUM
            elif diff_lower == 'hard':
                result = DIFFICULTY.HARD
            elif diff_lower == 'impossible':
                result = DIFFICULTY.IMPOSSIBLE
        elif DIFFICULTY.TRIVIAL <= difficulty <= DIFFICULTY.IMPOSSIBLE:
            result = difficulty
    except (ExtraConfig.DoesNotExist, KeyError):
        pass

    obj, _ = ProblemDifficulty.objects.get_or_create(problem=problem)
    obj.difficulty = result
    obj.save()
