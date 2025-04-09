from datetime import datetime, timedelta  # pylint: disable=E0611

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from pytz import UTC

from oioioi.base.permissions import make_request_condition
from oioioi.base.utils import request_cached, request_cached_complex
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
    UserResultForProblem,
    SubmissionMessage,
)
from oioioi.programs.models import ProgramsConfig
from oioioi.participants.models import TermsAcceptedPhrase

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
    
    def results_date(self):
        return self.show_results

    def public_results_visible(self, current_datetime):
        """Returns True if the results of the round have already been made
        public

        If the contest's controller makes no distinction between personal
        and public results, this function returns the same as
        :meth:'results_visible'.

        Otherwise the show_public_results date is used.
        """
        if not self.contest.controller.separate_public_results():
            return self.results_visible(current_datetime)

        if self.show_public_results is None:
            return False

        return current_datetime >= self.show_public_results
    
    def public_results_date(self):
        if not self.contest.controller.separate_public_results():
            return self.results_date()

        return self.show_public_results

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


@request_cached_complex
def visible_problem_instances(request, no_admin=False):
    controller = request.contest.controller
    queryset = (
        ProblemInstance.objects.filter(contest=request.contest)
        .select_related('problem')
        .prefetch_related('round')
    )
    return [pi for pi in queryset if controller.can_see_problem(
        request, pi, no_admin=no_admin,
    )]


@request_cached_complex
def visible_rounds(request, no_admin=False):
    controller = request.contest.controller
    queryset = Round.objects.filter(contest=request.contest)
    return [r for r in queryset if controller.can_see_round(
        request, r, no_admin=no_admin,
    )]

@make_request_condition
@request_cached
def are_rules_visible(request):
    return (
        hasattr(request, 'contest')
        and request.contest.show_contest_rules
    )

@request_cached
def get_number_of_rounds(request):
    """Returns the number of rounds in the current contest.
    """ 
    return Round.objects.filter(contest=request.contest).count()


def get_contest_dates(request):
    """Returns the end_date of the latest round and the start_date
    of the earliest round.
    """ 
    rtimes = rounds_times(request, request.contest)

    ends = [
        rt.get_end()
        for rt in rtimes.values()
    ]
    starts = [
        rt.get_start()
        for rt in rtimes.values()
    ]

    if starts and None not in starts:  
        min_start = min(starts)  
    else:  
        min_start = None

    if ends and None not in ends:  
        max_end = max(ends)
    else:  
        max_end = None

    return min_start, max_end


def get_scoring_desription(request):
    """Returns the scoring description of the current contest.
    """
    if (hasattr(request.contest.controller, 'scoring_description') and 
            request.contest.controller.scoring_description is not None):
        return request.contest.controller.scoring_description
    else:
        return None


@request_cached
def get_problems_sumbmission_limit(request):
    """Returns the upper and lower submission limit in the current contest.
    If there is one limit for all problems, it returns a list with one element.
    If there are no problems in the contest, it returns the default limit.
    """
    controller = request.contest.controller
    queryset = (
        ProblemInstance.objects.filter(contest=request.contest)
        .prefetch_related('round')
    )

    if queryset is None or not queryset.exists():
        return [Contest.objects.get(id=request.contest.id).default_submissions_limit]
    
    limits = set()
    for p in queryset:
        limits.add(controller.get_submissions_limit(request, p, noadmin=True))

    if len(limits) == 1:
        if None in limits:
            return None
        elif 0 in limits:
            return [_('infinity')]
        else:
            return [limits.pop()]
    elif len(limits) > 1:
        if 0 in limits:
            limits.remove(0)
            max_limit = _('infinity')
        else:
            max_limit = max(limits)

        min_limit = min(limits)

    return [min_limit, max_limit]


def get_results_visibility(request):
    """Returns the results ad ranking visibility for each round in the contest"""
    rtimes = rounds_times(request, request.contest)

    dates = list()
    for r in rtimes.keys():
        results_date = rtimes[r].results_date()
        public_results_date = rtimes[r].public_results_date()

        if results_date is None or results_date <= request.timestamp:
            results = _('immediately')
        else:
            results = _('after %(date)s') % {"date": results_date.strftime("%Y-%m-%d %H:%M:%S")}

        if public_results_date is None or public_results_date <= request.timestamp:
            ranking = _('immediately')
        else:
            ranking = _('after %(date)s') % {"date": public_results_date.strftime("%Y-%m-%d %H:%M:%S")}

        dates.append({
            'name' : r.name,
            'results' : results,
            'ranking' : ranking
        })

    return dates


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
    
def visible_contests_query(request):
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
    return Contest.objects.filter(visible_query).distinct()

@request_cached
def visible_contests(request):
    contests = visible_contests_query(request)
    return set(contests)

@request_cached_complex
def visible_contests_queryset(request, filter_value):
    contests = visible_contests_query(request)
    contests = contests.filter(Q(name__icontains=filter_value) | Q(id__icontains=filter_value) | Q(school_year=filter_value))    
    return set(contests)

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


@make_request_condition
@request_cached
def is_contest_owner(request):
    """Checks if the user is the owner of the current contest.
    This permission level allows full access to all contest functionality
    and additionally permits managing contest permissions for a given contest
    with the exception of contest ownerships.
    """
    return request.user.has_perm('contests.contest_owner', request.contest)


@make_request_condition
@request_cached
def is_contest_admin(request):
    """Checks if the user is the contest admin of the current contest.
    This permission level allows full access to all contest functionality.
    """
    return request.user.has_perm('contests.contest_admin', request.contest)


def can_admin_contest(user, contest):
    """Checks if the user should be allowed on the admin pages of the contest."""
    return user.has_perm('contests.contest_basicadmin', contest)


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


def get_submission_message(request):
    return get_public_message(
        request,
        SubmissionMessage,
        'submission_message',
    )


@make_request_condition
@request_cached
def is_contest_archived(request):
    return (
        hasattr(request, 'contest')
        and (request.contest is not None)
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

# The whole section below requires refactoring,
# may include refactoring the models of `Contest`, `ProgramsConfig` and `TermsAcceptedPhrase`

def extract_programs_config_execution_mode(request):
    return request.POST.get('programs_config-0-execution_mode', None)


def create_programs_config(request, adding):
    """Creates ProgramsConfig for a given contest if needed.

    Args:
        request: The HTTP request object.
        adding (bool): If True, the contest is being added; otherwise, it is being modified.
    """
    requested_contest_id = request.POST.get('id', None)
    execution_mode = extract_programs_config_execution_mode(request)

    if (
        execution_mode and
        execution_mode != 'AUTO'
    ):
        if adding and requested_contest_id:
            ProgramsConfig.objects.create(contest_id=requested_contest_id, execution_mode=execution_mode)
        elif not hasattr(request.contest, 'programs_config'):
            ProgramsConfig.objects.create(contest_id=request.contest.id, execution_mode=execution_mode)


def extract_terms_accepted_phrase_text(request):
    return request.POST.get('terms_accepted_phrase-0-text', None)


def create_terms_accepted_phrase(request, adding):
    """Creates TermsAcceptedPhrase for a given contest if needed.

    Args:
        request: The HTTP request object.
        adding (bool): If True, the contest is being added; otherwise, it is being modified.
    """

    requested_contest_id = request.POST.get('id', None)
    text = extract_terms_accepted_phrase_text(request)

    if text:
        if adding and requested_contest_id:
            TermsAcceptedPhrase.objects.create(contest_id=requested_contest_id, text=text)
        elif not hasattr(request.contest, 'terms_accepted_phrase'):
            TermsAcceptedPhrase.objects.create(contest_id=request.contest.id, text=text)


def create_contest_attributes(request, adding):
    """Called to create certain attributes of contest object after modifying it that would not be created automatically.
    Creates attributes are ProgramsConfig and TermsAcceptedPhrase

    Args:
        request: The HTTP request object.
        adding (bool): If True, the contest is being added; otherwise, it is being modified.
    """
    if request.method != 'POST':
        return
    create_programs_config(request, adding)
    create_terms_accepted_phrase(request, adding)

def get_problem_statements(request, controller, problem_instances):
    # Problem statements in order
    # 1) problem instance
    # 2) statement_visible
    # 3) round end time
    # 4) user result
    # 5) number of submissions left
    # 6) submissions_limit
    # 7) can_submit
    # Sorted by (start_date, end_date, round name, problem name)
    return sorted(
        [
            (
                pi,
                controller.can_see_statement(request, pi),
                controller.get_round_times(request, pi.round),
                # Because this view can be accessed by an anynomous user we can't
                # use `user=request.user` (it would cause TypeError). Surprisingly
                # using request.user.id is ok since for AnynomousUser id is set
                # to None.
                next(
                    (
                        r
                        for r in UserResultForProblem.objects.filter(
                            user__id=request.user.id, problem_instance=pi
                        )
                        if r
                        and r.submission_report
                        and controller.can_see_submission_score(
                            request, r.submission_report.submission
                        )
                    ),
                    None,
                ),
                pi.controller.get_submissions_left(request, pi),
                pi.controller.get_submissions_limit(request, pi),
                controller.can_submit(request, pi) and not is_contest_archived(request),
            )
            for pi in problem_instances
        ],
        key=lambda p: (p[2].get_key_for_comparison(), p[0].round.name, p[0].short_name),
    )
