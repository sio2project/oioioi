from datetime import datetime, timedelta  # pylint: disable=E0611

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string
from pytz import UTC

from oioioi.base.permissions import make_request_condition
from oioioi.base.utils import request_cached
from oioioi.base.utils.public_message import get_public_message
from oioioi.base.utils.query_helpers import Q_always_false
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Round,
    RoundTimeExtension,
    Submission,
    FilesMessage,
    SubmissionsMessage,
    SubmitMessage,
)


class RoundTimes(object):
    def __init__(
        self,
        start,
        end,
        contest,
        show_results=None,
        show_public_results=None,
        extra_time=0,
    ):
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
        return not (self.is_past(current_datetime) or self.is_future(current_datetime))

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
            return current_datetime >= self.show_results + timedelta(
                minutes=self.extra_time
            )

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

    def get_key_for_comparison(self):
        return (
            self.get_start() or UTC.localize(datetime.min),
            self.get_end() or UTC.localize(datetime.max),
        )


def generic_rounds_times(request=None, contest=None):
    if contest is None and not hasattr(request, 'contest'):
        return {}
    contest = contest or request.contest

    cache_attribute = '_generic_rounds_times_cache'
    if request is not None:
        if not hasattr(request, cache_attribute):
            setattr(request, cache_attribute, {})
        elif contest.id in getattr(request, cache_attribute):
            return getattr(request, cache_attribute)[contest.id]

    rounds = [
        r for r in Round.objects.filter(contest=contest).select_related('contest')
    ]
    rids = [r.id for r in rounds]
    if not request or not hasattr(request, 'user') or request.user.is_anonymous:
        rtexts = {}
    else:
        rtexts = dict(
            (x['round_id'], x)
            for x in RoundTimeExtension.objects.filter(
                user=request.user, round__id__in=rids
            ).values()
        )

    result = dict(
        (
            r,
            RoundTimes(
                r.start_date,
                r.end_date,
                r.contest,
                r.results_date,
                r.public_results_date,
                rtexts[r.id]['extra_time'] if r.id in rtexts else 0,
            ),
        )
        for r in rounds
    )
    if request is not None:
        getattr(request, cache_attribute)[contest.id] = result
    return result


def rounds_times(request, contest):
    return generic_rounds_times(request, contest)


@make_request_condition
def contest_exists(request):
    return hasattr(request, 'contest') and request.contest is not None


@make_request_condition
def has_any_rounds(request_or_context):
    return Round.objects.filter(contest=request_or_context.contest).exists()


@make_request_condition
@request_cached
def has_any_active_round(request):
    controller = request.contest.controller
    for round in Round.objects.filter(contest=request.contest):
        rtimes = controller.get_round_times(request, round)
        if rtimes.is_active(request.timestamp):
            return True
    return False


def _public_results_visible(request, **kwargs):
    controller = request.contest.controller
    for round in Round.objects.filter(contest=request.contest, **kwargs):
        rtimes = controller.get_round_times(request, round)
        if not rtimes.public_results_visible(request.timestamp):
            return False
    return True


@make_request_condition
@request_cached
def all_public_results_visible(request):
    """Checks if results of all rounds of the current contest are visible to
    public.
    """
    return _public_results_visible(request)


@make_request_condition
@request_cached
def all_non_trial_public_results_visible(request):
    """Checks if results of all non-trial rounds of the current contest are
    visible to public.
    """
    return _public_results_visible(request, is_trial=False)


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
    queryset = (
        ProblemInstance.objects.filter(contest=request.contest)
        .select_related('problem')
        .prefetch_related('round')
    )
    return [pi for pi in queryset if controller.can_submit(request, pi)]


@request_cached
def visible_problem_instances(request):
    controller = request.contest.controller
    queryset = (
        ProblemInstance.objects.filter(contest=request.contest)
        .select_related('problem')
        .prefetch_related('round')
    )
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


def used_controllers():
    """Returns list of dotted paths to contest controller classes in use
    by contests on this instance.
    """
    return Contest.objects.values_list('controller_name', flat=True).distinct()


@request_cached
def visible_contests(request):
    """Returns materialized set of contests visible to the logged in user."""
    if request.GET.get('living', 'safely') == 'dangerously':
        visible_query = Contest.objects.none()
        for controller_name in used_controllers():
            controller_class = import_string(controller_name)
            # HACK: we pass None contest just to call visible_contests_query.
            # This is a workaround for mixins not taking classmethods very well.
            controller = controller_class(None)
            subquery = Contest.objects.filter(controller_name=controller_name).filter(
                controller.registration_controller().visible_contests_query(request)
            )
            visible_query = visible_query.union(subquery, all=False)
        return set(visible_query)
    visible_query = Q_always_false()
    for controller_name in used_controllers():
        controller_class = import_string(controller_name)
        # HACK: we pass None contest just to call visible_contests_query.
        # This is a workaround for mixins not taking classmethods very well.
        controller = controller_class(None)
        visible_query |= Q(
            controller_name=controller_name
        ) & controller.registration_controller().visible_contests_query(request)
    return set(Contest.objects.filter(visible_query).distinct())


@request_cached
def administered_contests(request):
    """Returns a list of contests for which the logged
    user has contest_admin permission for.
    """
    return [
        contest
        for contest in visible_contests(request)
        if can_admin_contest(request.user, contest)
    ]


@request_cached
def administered_unarchived_contests(request):
    """Returns a list of unarchived contests for which the logged
    user has contest_admin permission for.
    """
    return [
        contest for contest in administered_contests(request) if not contest.is_archived
    ]


@make_request_condition
@request_cached
def is_contest_admin(request):
    """Checks if the user is the contest admin of the current contest.
    This permission level allows full access to all contest functionality.
    """
    return request.user.has_perm('contests.contest_admin', request.contest)


def can_admin_contest(user, contest):
    """Checks if the user should be allowed on the admin pages of the contest.
    This is the same level of permissions as is_contest_basicadmin.
    """
    return user.has_perm('contests.contest_admin', contest) or user.has_perm(
        'contests.contest_basicadmin', contest
    )


@make_request_condition
@request_cached
def is_contest_basicadmin(request):
    """Checks if the user is a basic admin of the current contest.
    This permission level allows edit access to basic contest functionality.
    It is also implied by having full admin privileges (is_contest_admin).
    """
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


def get_submission_or_error(request, submission_id, submission_class=Submission):
    """Returns the submission if it exists and user has rights to see it."""
    submission = get_object_or_404(submission_class, id=submission_id)
    if hasattr(request, 'user') and request.user.is_superuser:
        return submission
    pi = submission.problem_instance
    if pi.contest:
        if not request.contest or request.contest.id != pi.contest.id:
            raise PermissionDenied
        if is_contest_basicadmin(request) or is_contest_observer(request):
            return submission
    elif request.contest:
        raise PermissionDenied
    queryset = Submission.objects.filter(id=submission.id)
    if not pi.controller.filter_my_visible_submissions(request, queryset):
        raise PermissionDenied
    return submission


@request_cached
def last_break_between_rounds(request_or_context):
    """Returns the end_date of the latest past round and the start_date
    of the closest future round.

    Assumes that none of the rounds is active.
    """
    if isinstance(request_or_context, HttpRequest):
        rtimes = rounds_times(request_or_context, request_or_context.contest)
    else:
        rtimes = generic_rounds_times(None, request_or_context.contest)
    ends = [
        rt.get_end()
        for rt in rtimes.values()
        if rt.is_past(request_or_context.timestamp)
    ]
    starts = [
        rt.get_start()
        for rt in rtimes.values()
        if rt.is_future(request_or_context.timestamp)
    ]

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
            for round in Round.objects.filter(contest=contest)
        )
        next_rtimes = [(r, rt) for r, rt in rtimes.items() if rt.is_future(timestamp)]
        next_rtimes.sort(key=lambda r_rt: r_rt[1].get_start())
        current_rtimes = [
            (r, rt) for r, rt in rtimes if rt.is_active(timestamp) and rt.get_end()
        ]
        current_rtimes.sort(key=lambda r_rt1: r_rt1[1].get_end())
        past_rtimes = [(r, rt) for r, rt in rtimes.items() if rt.is_past(timestamp)]
        past_rtimes.sort(key=lambda r_rt2: r_rt2[1].get_end())

    if current_rtimes:
        return current_rtimes[0][0]
    elif next_rtimes:
        return next_rtimes[0][0]
    elif past_rtimes and allow_past_rounds:
        return past_rtimes[-1][0]
    else:
        return None


@make_request_condition
def has_any_contest(request):
    contests = [contest for contest in administered_contests(request)]
    return len(contests) > 0


def get_files_message(request):
    return get_public_message(
        request,
        FilesMessage,
        'files_message',
    )


def get_submissions_message(request):
    return get_public_message(
        request,
        SubmissionsMessage,
        'submissions_message',
    )


def get_submit_message(request):
    return get_public_message(
        request,
        SubmitMessage,
        'submit_message',
    )


@make_request_condition
@request_cached
def is_contest_archived(request):
    return (
        hasattr(request, 'contest')
        and request.contest.is_archived
    )


def get_inline_for_contest(inline, contest):
    """Returns inline without add, change or delete permissions,
    with all fields in readonly for archived contests.
    For unarchived contests returns the inline itself.
    """
    if not contest or not contest.is_archived:
        return inline

    class ArchivedInlineWrapper(inline):
        extra = 0
        max_num = 0
        can_delete = False
        editable_fields = []
        exclude = []

        def has_add_permission(self, request, obj=None):
            return False

        def has_change_permission(self, request, obj=None):
            return False

        def has_delete_permission(self, request, obj=None):
            return False

        def has_view_permission(self, request, obj=None):
            return True

    return ArchivedInlineWrapper
