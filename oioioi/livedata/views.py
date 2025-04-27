import datetime
import functools

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import dateformat
from django.utils.translation import get_language
from oioioi.base.permissions import enforce_condition
from oioioi.base.utils import allow_cross_origin, jsonify
from oioioi.contests.models import SubmissionReport
from oioioi.contests.utils import contest_exists, is_contest_admin, is_contest_observer
from oioioi.livedata.utils import can_see_livedata, get_display_name
from oioioi.problems.models import ProblemName

RESULT_FOR_FROZEN_SUBMISSION = 'FROZEN'


def cache_unless_admin_or_observer(view):
    @functools.wraps(view)
    def inner(request, round_id):
        should_cache = not is_contest_admin(request) and not is_contest_observer(
            request
        )
        if not should_cache:
            return view(request, round_id)

        cache_key = '%s/%s/%s' % (view.__name__, request.contest.id, round_id)
        result = cache.get(cache_key)
        if result is None:
            result = view(request, round_id)
            assert isinstance(result, HttpResponse)
            cache.set(
                cache_key,
                {
                    'content': result.content.decode(result.charset),
                    'content_type': result['Content-Type'],
                },
                settings.LIVEDATA_CACHE_TIMEOUT,
            )
        else:
            result = HttpResponse(
                result['content'], content_type=result['content_type']
            )
        return result

    return inner


@allow_cross_origin
@enforce_condition(contest_exists & can_see_livedata)
@cache_unless_admin_or_observer
@jsonify
def livedata_teams_view(request, round_id):
    return [
        {
            'id': participant.user.id,
            'login': participant.user.username,
            'name': get_display_name(participant.user),
        }
        for participant in request.contest.participant_set.all()
    ]


@allow_cross_origin
@enforce_condition(contest_exists & can_see_livedata)
@cache_unless_admin_or_observer
@jsonify
def livedata_tasks_view(request, round_id):
    round = get_object_or_404(request.contest.round_set.all(), pk=round_id)

    if not request.contest.controller.can_see_round(request, round):
        return []

    pis = (
        round.probleminstance_set.all()
        .prefetch_related('problem__names')
        .annotate(
            problem_localized_name=Subquery(
                ProblemName.objects.filter(
                    problem=OuterRef('problem__pk'), language=get_language()
                ).values('name')
            )
        )
    )
    problem_localized_name = F('problem_localized_name')

    return [
        {'id': pi.id, 'shortName': pi.short_name, 'name': pi.problem.name}
        for pi in pis.order_by(problem_localized_name.asc(nulls_first=True))
    ]


@allow_cross_origin
@enforce_condition(contest_exists & can_see_livedata)
@cache_unless_admin_or_observer
@jsonify
def livedata_events_view(request, round_id):
    user_is_participant = Q(
        submission__user__participant__contest_id=request.contest.id,
        submission__user__participant__status='ACTIVE',
    )
    submission_ignored = Q(submission__kind='IGNORED')

    reports = (
        SubmissionReport.objects.filter(user_is_participant)
        .exclude(submission_ignored)
        .exclude(kind='TESTRUN')
        .select_related('submission')
        .prefetch_related('scorereport_set')
    )

    if (
        is_contest_admin(request) or is_contest_observer(request)
    ) and 'from' in request.GET:
        # Only admin/observer is allowed to specify 'from' parameter.
        start_time = datetime.datetime.utcfromtimestamp(
            int(request.GET['from'])
        ).replace(tzinfo=datetime.timezone.utc)
        reports = reports.filter(creation_date__gte=start_time)

    round = get_object_or_404(request.contest.round_set.all(), pk=round_id)
    contest_start = round.start_date
    reports = reports.filter(submission__problem_instance__round=round)
    if is_contest_admin(request):
        freeze_time = None
    else:
        freeze_time = request.contest.controller.get_round_freeze_time(round)

    if round.results_date is not None and request.timestamp > round.results_date:
        freeze_time = None

    return [
        {
            'submissionId': 'START',
            'reportId': 'START',
            'teamId': 'START',
            'taskId': 'START',
            'submissionTimestamp': int(dateformat.format(request.timestamp, 'U')),
            'judgingTimestamp': int(dateformat.format(contest_start, 'U')),
            'result': 'CTRL',
        }
    ] + [
        {
            'submissionId': report.submission_id,
            'reportId': report.pk,
            'teamId': report.submission.user_id,
            'taskId': report.submission.problem_instance_id,
            'submissionTimestamp': int(dateformat.format(report.submission.date, 'U')),
            'judgingTimestamp': int(dateformat.format(report.creation_date, 'U')),
            'result': report.score_report.status
            if freeze_time is None or report.submission.date < freeze_time
            else RESULT_FOR_FROZEN_SUBMISSION,
        }
        for report in reports.order_by('creation_date')
        if report.score_report is not None
    ]
