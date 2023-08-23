from django.template.loader import render_to_string

from oioioi.base.utils import request_cached
from oioioi.base.permissions import make_request_condition
from oioioi.programs.controllers import ProgrammingContestController


def render_head(requirements):
    """For a given list of paths for required files produces a HTML which
    includes the paths. The output contains only unique paths. Currently
    supported extensions: .css .js
    Order of the included paths is stable.
    """
    unique = set()
    result = ''
    prefix = '/static/'

    for name in requirements:
        if name not in unique:
            unique.add(name)
            ext = name.split('.')[-1].strip().lower()
            if ext == 'css':
                result += render_to_string(
                    'statistics/include-css.html', {'file_name': prefix + name}
                )
            if ext == 'js':
                result += render_to_string(
                    'statistics/include-js.html', {'file_name': prefix + name}
                )
    return result


@make_request_condition
@request_cached
def any_statistics_avaiable(request):
    controller = request.contest.controller
    if not isinstance(controller, ProgrammingContestController):
        return False
    return bool(controller.statistics_available_plot_groups(request))


@make_request_condition
@request_cached
def can_see_stats(request):
    return request.contest.controller.can_see_stats(request)
