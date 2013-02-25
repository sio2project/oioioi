from django.core.exceptions import PermissionDenied
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        Submission, RoundTimeExtension
from oioioi.base.utils import request_cached
from datetime import timedelta

class RoundTimes(object):
    def __init__(self, start, end, show_results, extra_time=0):
        self.start = start
        self.end = end
        self.show_results = show_results
        self.extra_time = extra_time

    def is_past(self, current_datetime):
        """Returns True if the round is over for a user"""
        end = self.get_end()
        return end is not None and current_datetime > end

    def is_active(self, current_datetime):
        """Returns True if the round is still active for a user"""
        return not (self.is_past(current_datetime) or
                    self.is_future(current_datetime))

    def is_future(self, current_datetime):
        """Returns True if the round is not started for a user"""
        start = self.get_start()
        return start is not None and current_datetime < start

    def results_visible(self, current_datetime):
        return self.show_results is not None and \
               current_datetime >= self.show_results

    def get_start(self):
        return self.start

    def get_end(self):
        """Returns end of user roundtime
           having regard to the extension of the rounds
        """
        if self.end:
            return self.end + timedelta(minutes=self.extra_time)
        else:
            return self.end

@request_cached
def rounds_times(request):
    if not hasattr(request, 'contest'):
        return {}

    rounds = [r for r in Round.objects.filter(contest=request.contest)]
    rids = [r.id for r in rounds]
    if request.user.is_anonymous():
        rtexts = {}
    else:
        rtexts = dict(map(lambda x: (x['round_id'], x),
                          RoundTimeExtension.objects
                            .filter(user=request.user, round__id__in=rids)
                            .values()))

    return dict((r, RoundTimes(r.start_date, r.end_date, r.results_date,
                          rtexts[r.id]['extra_time'] if r.id in rtexts else 0))
            for r in rounds)

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
    return bool(submittable_problem_instances(request))

@request_cached
def has_any_visible_problem_instance(request):
    return bool(visible_problem_instances(request))

@request_cached
def submittable_problem_instances(request):
    controller = request.contest.controller
    queryset = ProblemInstance.objects.filter(contest=request.contest) \
            .select_related('problem').prefetch_related('round')
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

def check_submission_access(request, submission):
    if submission.problem_instance.contest != request.contest:
        raise PermissionDenied
    if request.user.has_perm('contests.contest_admin', request.contest):
        return
    controller = request.contest.controller
    queryset = Submission.objects.filter(id=submission.id)
    if not controller.filter_visible_submissions(request, queryset):
        raise PermissionDenied
