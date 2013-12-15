from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from oioioi.base.permissions import make_request_condition
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
        """Returns True if results are visible for a user.

           Usually show_results date decides.

           When a RoundTimeExtension is set for a given user and the round
           is still active, results publication is delayed.
        """
        if self.show_results is None:
            return False

        if self.is_active(current_datetime):
            return current_datetime >= \
                    self.show_results + timedelta(minutes=self.extra_time)

        return current_datetime >= self.show_results

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
        rtexts = dict((x['round_id'], x) for x in RoundTimeExtension.objects
                      .filter(user=request.user, round__id__in=rids).values())

    return dict((r, RoundTimes(r.start_date, r.end_date, r.results_date,
                          rtexts[r.id]['extra_time'] if r.id in rtexts else 0))
            for r in rounds)


@make_request_condition
def contest_exists(request):
    return hasattr(request, 'contest') and request.contest is not None


@make_request_condition
def has_any_rounds(request):
    return Round.objects.filter(contest=request.contest).exists()


@make_request_condition
@request_cached
def has_any_active_round(request):
    controller = request.contest.controller
    for round in Round.objects.filter(contest=request.contest):
        rtimes = controller.get_round_times(request, round)
        if rtimes.is_active(request.timestamp):
            return True
    return False


@make_request_condition
@request_cached
def has_any_submittable_problem(request):
    return bool(submittable_problem_instances(request))


@make_request_condition
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

    failures = [s for s in statuses if s != 'OK']
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


@make_request_condition
@request_cached
def is_contest_admin(request):
    """Checks if the current user can administer the current contest."""
    return request.user.has_perm('contests.contest_admin', request.contest)


@make_request_condition
@request_cached
def is_contest_observer(request):
    """Checks if the current user can observe the current contest."""
    return request.user.has_perm('contests.contest_observer', request.contest)


@make_request_condition
@request_cached
def can_enter_contest(request):
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_enter_contest(request)


def get_submission_or_error(request, contest_id, submission_id,
                          submission_class=Submission):
    """Returns the submission if it exists and user has rights to see it."""
    submission = get_object_or_404(submission_class, id=submission_id)
    if request.contest.id != submission.problem_instance.contest_id:
        raise PermissionDenied
    if is_contest_admin(request) or is_contest_observer(request):
        return submission
    controller = request.contest.controller
    queryset = Submission.objects.filter(id=submission.id)
    if not controller.filter_my_visible_submissions(request, queryset):
        raise PermissionDenied
    return submission
