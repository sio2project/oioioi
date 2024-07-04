from collections import defaultdict
from datetime import datetime, timedelta
from pprint import pprint

from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import F
from humanize import naturaldelta

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import ProblemInstance, ContestPermission, contest_permissions, ContestAttachment, \
    Submission, SubmissionReport, RoundTimeExtension, ScoreReport
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_admin,
    is_contest_observer, rounds_times,
)
from oioioi.participants.models import Participant
from oioioi.programs.models import Test
from oioioi.questions.models import Message
from oioioi.statistics.controllers import statistics_categories
from oioioi.evalmgr.models import QueuedJob
from oioioi.statistics.utils import any_statistics_avaiable, can_see_stats, render_head
from oioioi.testrun.models import TestRunConfig


def links(request):
    controller = request.contest.controller
    links_list = []
    plot_groups = controller.statistics_available_plot_groups(request)

    for (category, object_name, description) in plot_groups:
        category_name, link = statistics_categories[category]
        links_list.append(
            {
                'name': description,
                'category': category,
                'category_name': category_name,
                'link': link,
                'object': object_name,
            }
        )
    return links_list


@contest_admin_menu_registry.register_decorator(
    _("Statistics"),
    lambda request: reverse(
        'statistics_main', kwargs={'contest_id': request.contest.id}
    ),
    condition=(is_contest_admin | is_contest_observer),
    order=100,
)
@menu_registry.register_decorator(
    _("Statistics"),
    lambda request: reverse(
        'statistics_main', kwargs={'contest_id': request.contest.id}
    ),
    condition=(~is_contest_admin & ~is_contest_observer),
    order=100,
)
@enforce_condition(
    contest_exists & can_enter_contest & can_see_stats & any_statistics_avaiable
)
def statistics_view(
    request, category=statistics_categories['CONTEST'][1], object_name=''
):
    controller = request.contest.controller

    category_key = ''
    for (key, desc) in statistics_categories:
        if desc[1] == category:
            category_key = key
    category = category_key

    if category == 'PROBLEM':
        object = ProblemInstance.objects.get(
            short_name=object_name, contest=request.contest
        )
        title = _("Statistics for %s") % object.problem.name
    elif category == 'CONTEST':
        object = request.contest
        object_name = request.contest.id
        title = _("Contest statistics")
    else:
        raise Http404

    if not (category, object_name) in set(
        (c, o) for (c, o, d) in controller.statistics_available_plot_groups(request)
    ):
        raise PermissionDenied(_("You have no access to those charts"))

    plots = controller.statistics_available_plots(request, category, object)
    data_list = [
        controller.statistics_data(request, plot_kind, object)
        for plot_kind, object_name in plots
    ]

    plots_HTML, head_list = (
        []
        if not data_list
        else list(
            zip(
                *[
                    (
                        controller.render_statistics(request, data, id),
                        data['plot_type'].head_libraries(),
                    )
                    for id, data in enumerate(data_list)
                ]
            )
        )
    )

    return TemplateResponse(
        request,
        'statistics/stat.html',
        {
            'title': title,
            'head': render_head(sum(head_list, [])),
            'plots': plots_HTML,
            'links': links(request),
        },
    )


@contest_admin_menu_registry.register_decorator(
    _("Monitoring"),
    lambda request: reverse(
        'monitoring', kwargs={'contest_id': request.contest.id}
    ),
    condition=(is_contest_admin | is_contest_observer),
    order=110,
)
@enforce_condition(
    contest_exists & can_enter_contest & can_see_stats
)
def monitoring_view(request):
    q_size = QueuedJob.objects.filter(submission__problem_instance__contest=request.contest).count()
    q_size_global = QueuedJob.objects.count()
    sys_error_count = (
        SubmissionReport.objects.filter(status='ACTIVE', failurereport__isnull=False,
                                        submission__problem_instance__contest=request.contest).count()
        + SubmissionReport.objects.filter(status='ACTIVE', scorereport__status='SE',
                                          submission__problem_instance__contest=request.contest).count()
    )

    unanswered_questions = (Message.objects.filter(kind='QUESTION', message=None, contest=request.contest).count())
    oldest_unanswered_question = (Message.objects.filter(kind='QUESTION', message=None, contest=request.contest)
                                  .order_by('date').first())
    oldest_unanswered_question_date = oldest_unanswered_question.date if oldest_unanswered_question else None

    submissions_info = (Submission.objects.filter(problem_instance__contest=request.contest).values('kind')
                        .annotate(total=Count('kind')).order_by())
    rounds_info = get_rounds_info(request)
    permissions_info = get_permissions_info(request)
    attachments_info = get_attachments_info(request)
    tests_info = get_tests_info(request)

    def is_rte_active(rte):
        return rte['round__end_date'] + timedelta(minutes=rte['extra_time']) >= request.timestamp

    round_time_extensions = (RoundTimeExtension.objects.filter(round__contest=request.contest.id)
                             .values("round__name", "round__end_date", "extra_time")
                             .annotate(count=Count('extra_time'))
                             .order_by('extra_time'))

    active_rtes = list(filter(is_rte_active, round_time_extensions))

    return TemplateResponse(
        request,
        'statistics/monitoring.html',
        {
            'title': _("Monitoring"),
            'rounds_times': rounds_info,
            'permissions_info': permissions_info,
            'q_size': q_size,
            'q_size_global': q_size_global,
            'attachments': attachments_info,
            'unanswered_questions': unanswered_questions,
            'oldest_unanswered_question': oldest_unanswered_question_date,
            'submissions_info': submissions_info,
            'tests_info': tests_info,
            'sys_error_count': sys_error_count,
            'round_time_extensions': active_rtes,
        },
    )


def get_rounds_info(request):
    rounds_info = []
    for round_, rt in rounds_times(request, request.contest).items():
        round_time_info = {'name': str(round_), 'start': rt.start or _("Not set")}
        if rt.start:
            round_time_info['start_relative'] = naturaldelta(rt.start - request.timestamp) if rt.is_future(
                request.timestamp) else _("Started")
        else:
            round_time_info['start_relative'] = _("Not set")
        round_time_info['end'] = rt.end or _("Not set")
        if rt.end:
            round_time_info['end_relative'] = naturaldelta(rt.end - request.timestamp) if not rt.is_past(
                request.timestamp) else _("Finished")
        else:
            round_time_info['end_relative'] = _("Not set")
        rounds_info.append(round_time_info)
    return rounds_info


def get_attachments_info(request):
    attachments = ContestAttachment.objects.filter(contest_id=request.contest.id).order_by('id')
    for attachment in attachments:
        pub_date_relative = None
        if attachment.pub_date:
            pub_date_relative = naturaldelta(attachment.pub_date - request.timestamp) \
                if attachment.pub_date > request.timestamp else _("Published")
        setattr(attachment, 'pub_date_relative', pub_date_relative)
    return attachments


def get_permissions_info(request):
    permissions_info = {
        permission_name: (ContestPermission
                          .objects
                          .filter(contest_id=request.contest.id, permission=permission_cls)
                          .count())
        for permission_cls, permission_name in contest_permissions
    }
    permissions_info['Participant'] = Participant.objects.filter(contest_id=request.contest.id).count()
    return permissions_info





def get_tests_info(request):
    tests_info = defaultdict(lambda: defaultdict(lambda: {
        'problem_name': None,
        'testrun_config': None,
        'tests': list(),
        'submissions_limit': None,
        'solved': False,
    }))
    tests_qs = Test.objects.filter(problem_instance__contest=request.contest)
    tests_limits = (tests_qs.values('memory_limit', 'time_limit', 'problem_instance', 'problem_instance__round__name',
                                    'problem_instance__short_name', 'problem_instance',
                                    'problem_instance__submissions_limit')
                    .annotate(count=Count('problem_instance'))
                    .order_by('problem_instance', 'memory_limit', 'time_limit'))

    for t_info in tests_limits:
        tests_info[t_info['problem_instance__round__name']][t_info['problem_instance']]['tests'].append(t_info)
        tests_info[t_info['problem_instance__round__name']][t_info['problem_instance']]['problem_name'] = \
            t_info['problem_instance__short_name']
        tests_info[t_info['problem_instance__round__name']][t_info['problem_instance']]['submissions_limit'] = \
            t_info['problem_instance__submissions_limit']

    testrunconfig_qs = TestRunConfig.objects.filter(problem_instance__contest=request.contest)
    for trc in testrunconfig_qs:
        tests_info[trc.problem_instance.round.name][trc.problem_instance.id]['testrun_config'] = trc

    solved_qs = ScoreReport.objects.filter(submission_report__submission__problem_instance__contest=request.contest,
                                            submission_report__kind='NORMAL',
                                            submission_report__submission__kind='NORMAL',
                                            score = F('max_score'))

    for s in solved_qs:
        tests_info[s.submission_report.submission.problem_instance.round.name][s.submission_report.submission.problem_instance.id]['solved'] = True

    tests_info = dict({r: dict(t) for r, t in tests_info.items()})

    return tests_info
