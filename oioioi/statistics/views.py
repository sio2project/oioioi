from datetime import datetime
from pprint import pprint

from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pytz import UTC

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import ProblemInstance, ContestPermission, contest_permissions, ContestAttachment, \
    Submission, SubmissionReport
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_admin,
    is_contest_observer, rounds_times,
)
from oioioi.participants.models import Participant
from oioioi.questions.models import Message
from oioioi.statistics.controllers import statistics_categories
from oioioi.evalmgr.models import QueuedJob
from oioioi.statistics.utils import any_statistics_avaiable, can_see_stats, render_head


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
    cur_time = UTC.localize(datetime.now())
    r_times = []
    for round_, rt in rounds_times(request, request.contest).items():
        round_time_info = {'name': str(round_)}
        round_time_info['start'] = rt.start or _("Not set")
        if rt.start:
            round_time_info['start_relative'] = str(rt.start - cur_time)[:-7] if rt.is_future(cur_time) else _("Started")
        else:
            round_time_info['start_relative'] = _("Not set")
        round_time_info['end'] = rt.end or _("Not set")
        if rt.end:
            round_time_info['end_relative'] = str(rt.end - cur_time)[:-7] if not rt.is_past(cur_time) else _("Finished")
        else:
            round_time_info['end_relative'] = _("Not set")
        r_times.append(round_time_info)

    permissions_count = {
        permission_name: (ContestPermission
                          .objects
                          .filter(contest_id=request.contest.id, permission=permission_cls)
                          .count())
        for permission_cls, permission_name in contest_permissions
    }
    permissions_count['Participant'] = Participant.objects.filter(contest_id=request.contest.id).count()
    q_size = (QueuedJob.objects
                .filter(submission__problem_instance__contest=request.contest)
                .count())
    q_size_global = (QueuedJob.objects
                .count())

    sys_error_count = (
        SubmissionReport.objects.filter( status='ACTIVE', failurereport__isnull=False).count()
        +
        SubmissionReport.objects.filter( status='ACTIVE', testreport__status='SE').count()
    )

    attachments = ContestAttachment.objects.filter(contest_id=request.contest.id).order_by('id')
    for attachment in attachments:
        pub_date_relative = None
        if attachment.pub_date:
            pub_date_relative = str(attachment.pub_date - cur_time)[:-7] if attachment.pub_date > cur_time else _("Published")
        setattr(attachment, 'pub_date_relative', pub_date_relative)
    unanswered_questions = (Message.objects.filter(kind='QUESTION', message=None, contest=request.contest).count())
    oldest_unanswered_question = (Message.objects.filter(kind='QUESTION', message=None, contest=request.contest)
                                  .order_by('pub_date').first())
    oldest_unanswered_question_date = oldest_unanswered_question.date if oldest_unanswered_question else None

    submissions_info = Submission.objects.filter(problem_instance__contest=request.contest).values('kind').annotate(total=Count('kind')).order_by()

    return TemplateResponse(
        request,
        'statistics/monitoring.html',
        {
            'title': _("Monitoring"),
            'rounds_times': r_times,
            'permissions_count': permissions_count,
            'links': links(request),
            'q_size': q_size,
            'q_size_global': q_size_global,
            'attachments': attachments,
            'unanswered_questions': unanswered_questions,
            'oldest_unanswered_question': oldest_unanswered_question_date,
            'submissions_info': submissions_info,
            'sys_error_count': sys_error_count,
        },
    )
