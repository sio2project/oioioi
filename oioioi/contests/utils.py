from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.base.utils import request_cached

@request_cached
def has_any_active_round(request):
    controller = request.contest.controller
    for round in Round.objects.filter(contest=request.contest):
        rtimes = controller.get_round_times(request, round)
        if rtimes.is_active(request.timestamp):
            return True
    return False

@request_cached
def has_any_submittable_problem(request):
    controller = request.contest.controller
    for pi in ProblemInstance.objects.filter(contest=request.contest) \
            .select_related():
        if controller.can_submit(request, pi):
            return True
    return False

@request_cached
def has_any_visible_problem_instance(request):
    controller = request.contest.controller
    for pi in ProblemInstance.objects.filter(contest=request.contest) \
            .select_related('problem').prefetch_related('round'):
        if controller.can_see_problem(request, pi):
            return True
    return False

@request_cached
def submittable_problem_instances(request):
    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(contest=request.contest) \
            .select_related('problem')
    return [pi for pi in queryset if controller.can_submit(request, pi)]

@request_cached
def visible_problem_instances(request):
    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(contest=request.contest) \
            .select_related('problem').prefetch_related('round')
    return [pi for pi in queryset if controller.can_see_problem(request, pi)]

@request_cached
def visible_rounds(request):
    controller = request.contest.controller
    queryset = Round.objects.filter(contest=request.contest)
    return [r for r in queryset if controller.can_see_round(request, r)]

def aggregate_statuses(statuses):
    """Returns first unsuccessful status or 'OK' if all are successful"""

    failures = filter(lambda status: status != 'OK', statuses)
    if failures:
        return failures[0]
    else:
        return 'OK'

@request_cached
def visible_contests(request):
    contests = []
    for contest in Contest.objects.order_by('-creation_date'):
        rcontroller = contest.controller.registration_controller()
        if rcontroller.can_enter_contest(request):
            contests.append(contest)
    return contests

@request_cached
def is_contest_admin(request):
    """Checks if the current user can administer the current contest."""
    return request.user.has_perm('contests.contest_admin', request.contest)

@request_cached
def can_enter_contest(request):
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_enter_contest(request)
