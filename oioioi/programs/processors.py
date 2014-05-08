from django.core.context_processors import csrf
from django.template.loader import render_to_string
from django.utils.functional import lazy

from oioioi.programs.controllers import ProgrammingContestController
from oioioi.contests.utils import can_enter_contest, contest_exists, \
        has_any_submittable_problem


def drag_and_drop_processor(request):
    if not hasattr(request, 'resolver_match'):
        return {}

    # here add names of named URLs (as in patterns in urls.py)
    # for which drag and drop zone will be hidden
    urls_to_hide = ['submit', 'testrun_submit']
    current_url_name = request.resolver_match.url_name

    if current_url_name in urls_to_hide:
        return {}

    def ddzone_generator():
        # show drag and drop zone only for contest with submitting some files
        if not hasattr(request, 'contest') or \
                not hasattr(request.contest, 'controller') or \
                not isinstance(request.contest.controller,
                               ProgrammingContestController):
            return ''
        # do not show drag and drop zone when no available problems
        # (the following require controller in request)
        if not has_any_submittable_problem(request) \
                or not contest_exists(request) \
                or not can_enter_contest(request) \
                or getattr(request, 'hide_drag_and_drop', False):
            return ''

        c = {'contest_id': request.contest.id}
        c.update(csrf(request))
        return render_to_string('programs/drag_and_drop.html', c)

    return {'extra_footer_drag_and_drop': lazy(ddzone_generator, unicode)()}
