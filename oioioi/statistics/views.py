from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import ProblemInstance
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    is_contest_admin,
    is_contest_observer,
)
from oioioi.statistics.controllers import statistics_categories
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
def monitoring_view(request):
    return TemplateResponse(
        request,
        'statistics/monitoring.html',
        {
            'title': 'Monitoring',
            'links': links(request),
        },
    )
