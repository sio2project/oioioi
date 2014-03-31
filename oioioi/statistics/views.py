from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse
from oioioi.base.menu import menu_registry
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.statistics.utils import render_head, any_statistics_avaiable, \
         can_see_stats
from oioioi.statistics.controllers import statistics_categories
from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists, can_enter_contest, \
        is_contest_admin, is_contest_observer
from oioioi.contests.models import ProblemInstance

def links(request):
    controller = request.contest.controller
    links_list = []
    plot_groups = controller.statistics_available_plot_groups(request)

    for (category, object_name, description) in plot_groups:
        category_name, link = statistics_categories[category]
        links_list.append({
            'name': description,
            'category': category,
            'category_name': category_name,
            'link': link,
            'object': object_name
        })
    return links_list


@contest_admin_menu_registry.register_decorator(_("Statistics"),
                                                lambda request:
        reverse('statistics_main', kwargs={'contest_id': request.contest.id}),
        condition=(is_contest_admin | is_contest_observer),
        order=100)
@menu_registry.register_decorator(_("Statistics"), lambda request:
        reverse('statistics_main', kwargs={'contest_id': request.contest.id}),
        condition=(~is_contest_admin & ~is_contest_observer),
        order=100)
@enforce_condition(contest_exists & can_enter_contest & can_see_stats
                   & any_statistics_avaiable)
def statistics_view(request, contest_id,
                    category=statistics_categories['CONTEST'][1],
                    object_name=''):
    controller = request.contest.controller

    category_key = ''
    for (key, desc) in statistics_categories:
        if desc[1] == category:
            category_key = key
    category = category_key

    title = ''
    if category == 'PROBLEM':
        problem = ProblemInstance.objects.filter(short_name=object_name, contest=request.contest)[0]
        title = _('Statistics for %s') % problem.problem.name
        object = problem
    if category == 'CONTEST':
        object = request.contest

    plots = controller.statistics_available_plots(request,
                                                  category, object)

    data_list = []
    for plot_kind, object_name in plots:
        data_piece = controller.statistics_data(request,
                                                plot_kind, object)
        data_list.append(data_piece)

    if data_list == []:  # zip does not like empty lists
        return TemplateResponse(request, 'statistics/stat.html',
                                {'title': title})

    (plots_HTML, head_list) = zip(*[
        (controller.render_statistics(request, data, id),
        data['plot_type'].head_libraries())
        for id, data in enumerate(data_list)])

    head_libs = sum(head_list, [])

    links_dict = links(request)

    context = {
       'title': title,
       'head': render_head(head_libs),
       'plots': plots_HTML,
       'links': links_dict
    }
    return TemplateResponse(request, 'statistics/stat.html', context)
