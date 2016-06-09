from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from oioioi.base.permissions import make_request_condition
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        Submission, RoundTimeExtension
from oioioi.base.utils import request_cached
from datetime import timedelta
from collections import defaultdict


class RoundTimes(object):
    def __init__(self, start, end, contest, show_results=None,
            show_public_results=None, extra_time=0):
        self.start = start
        self.end = end
        self.show_results = show_results
        self.show_public_results = show_public_results
        self.contest = contest
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

    def public_results_visible(self, current_datetime):
        """Returns True if the results of the round have already been made
           public

           It the contest's controller makes no distinction between personal
           and public results, this function returns the same as
           :meth:'results_visible'.

           Otherwise the show_public_results date is used.
        """
        if not self.contest.controller.separate_public_results():
            return self.results_visible(current_datetime)

        if self.show_public_results is None:
            return False

        return current_datetime >= self.show_public_results

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

    rounds = [r for r in Round.objects.filter(contest=request.contest)
              .select_related('contest')]
    rids = [r.id for r in rounds]
    if not request.user or request.user.is_anonymous():
        rtexts = {}
    else:
        rtexts = dict((x['round_id'], x) for x in RoundTimeExtension.objects
                      .filter(user=request.user, round__id__in=rids).values())

    return dict((r, RoundTimes(r.start_date, r.end_date, r.contest,
        r.results_date, r.public_results_date,
        rtexts[r.id]['extra_time'] if r.id in rtexts else 0)) for r in rounds)


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
def all_public_results_visible(request):
    """Checks if results of all rounds of the current contest are visible to
       public.
    """
    controller = request.contest.controller
    for round in Round.objects.filter(contest=request.contest):
        rtimes = controller.get_round_times(request, round)
        if not rtimes.public_results_visible(request.timestamp):
            return False
    return True


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


def contests_by_registration_controller():
    """Returns a mapping from RegistrationController class to contest ids.

       This is useful for limiting the number of database queries required
       to check which contests can be shown to the user.  It allows
       RegistrationController subclasses to operate on contest querysets
       and filter many of them at once.

       :rtype: :class:`~collections.defaultdict` containing `set` objects
    """
    rcontrollers = defaultdict(set)
    for contest in Contest.objects.all():
        rc = contest.controller.registration_controller()
        rcontrollers[rc.__class__].add(contest.id)
    return rcontrollers

@request_cached
def visible_contests(request):
    visible = set()
    rc_mapping = contests_by_registration_controller()
    for rcontroller, contest_ids in rc_mapping.iteritems():
        contests = Contest.objects.filter(id__in=contest_ids)
        # These querysets could be concatenated and evaluated in a single
        # query, however it turns out, that it results in so big and complex
        # WHERE clauses that Postgres doesn't even attempt to optimize it
        # (which means ~100x longer execution times).
        filtered = set(rcontroller.filter_visible_contests(request, contests))
        visible = visible | filtered
    return visible


def can_admin_contest(user, contest):
    """Checks if the user can administer the contest."""
    return user.has_perm('contests.contest_admin', contest)


@make_request_condition
@request_cached
def is_contest_admin(request):
    """Checks if the current user can administer the current contest."""
    return can_admin_contest(request.user, request.contest)


@make_request_condition
@request_cached
def is_contest_observer(request):
    """Checks if the current user can observe the current contest."""
    return request.user.has_perm('contests.contest_observer', request.contest)


@make_request_condition
@request_cached
def can_see_personal_data(request):
    """Checks if the current user has permission to see personal data."""
    return request.user.has_perm('contests.personal_data', request.contest)


@make_request_condition
@request_cached
def can_enter_contest(request):
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_enter_contest(request)


def get_submission_or_error(request, submission_id,
                            submission_class=Submission):
    """Returns the submission if it exists and user has rights to see it."""
    submission = get_object_or_404(submission_class, id=submission_id)
    pi = submission.problem_instance
    if pi.contest:
        if not request.contest or request.contest.id != pi.contest.id:
            raise PermissionDenied
        if is_contest_admin(request) or is_contest_observer(request):
            return submission
    elif request.contest:
        raise PermissionDenied
    queryset = Submission.objects.filter(id=submission.id)
    if not pi.controller.filter_my_visible_submissions(request, queryset):
        raise PermissionDenied
    return submission


@request_cached
def last_break_between_rounds(request):
    """Returns the end_date of the latest past round and the start_date
       of the closest future round.

       Assumes that none of the rounds is active.
    """
    rtimes = rounds_times(request)
    ends = [rt.get_end() for rt in rtimes.itervalues()
            if rt.is_past(request.timestamp)]
    starts = [rt.get_start() for rt in rtimes.itervalues()
              if rt.is_future(request.timestamp)]

    max_end = max(ends) if ends else None
    min_start = min(starts) if starts else None

    return max_end, min_start


def best_round_to_display(request, allow_past_rounds=False):
    timestamp = getattr(request, 'timestamp', None)
    contest = getattr(request, 'contest', None)

    next_rtimes = None
    current_rtimes = None
    past_rtimes = None

    if timestamp and contest:
        rtimes = dict(
                (round, contest.controller.get_round_times(request, round))
                for round in Round.objects.filter(contest=contest))
        next_rtimes = [(r, rt) for r, rt in rtimes.iteritems()
                if rt.is_future(timestamp)]
        next_rtimes.sort(key=lambda (r, rt): rt.get_start())
        current_rtimes = [(r, rt) for r, rt in rtimes
                                if rt.is_active(timestamp) and rt.get_end()]
        current_rtimes.sort(key=lambda (r, rt): rt.get_end())
        past_rtimes = [(r, rt) for r, rt in rtimes.iteritems()
                if rt.is_past(timestamp)]
        past_rtimes.sort(key=lambda (r, rt): rt.get_end())

    if current_rtimes:
        return current_rtimes[0][0]
    elif next_rtimes:
        return next_rtimes[0][0]
    elif past_rtimes and allow_past_rounds:
        return past_rtimes[-1][0]
    else:
        return None
