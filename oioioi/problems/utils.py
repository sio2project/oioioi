from oioioi.base.utils import request_cached
from oioioi.contests.utils import is_contest_admin


@request_cached
def can_add_problems(request):
    return request.user.has_perm('problems.problems_db_admin') \
            or is_contest_admin(request)


def can_change_problem(request, problem):
    if request.user.has_perm('problems.problems_db_admin'):
        return True
    if request.user.has_perm('problems.problem_admin', problem):
        return True
    if problem.contest and request.user.has_perm('contests.contest_admin',
            problem.contest):
        return True
    return False
