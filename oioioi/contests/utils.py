from django.template.response import TemplateResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Contest
import functools

def aggregate_statuses(statuses):
    """Returns first unsuccessful status or 'OK' if all are successful"""

    failures = filter(lambda status: status != 'OK', statuses)
    if failures:
        return failures[0]
    else:
        return 'OK'

def visible_contests(request):
    contests = []
    for contest in Contest.objects.order_by('-creation_date'):
        rcontroller = contest.controller.registration_controller()
        if rcontroller.can_enter_contest(request):
            contests.append(contest)
    return contests

def enter_contest_permission_required(fn):
    @functools.wraps(fn)
    def wrapped(request, *args, **kwargs):
        if not request.contest:
            return TemplateResponse(request, "index-no-contests.html")
        rcontroller = request.contest.controller.registration_controller()
        if not rcontroller.can_enter_contest(request):
            return rcontroller.no_entry_view(request)
        return fn(request, *args, **kwargs)
    return wrapped

def contest_admin_permission_required(fn):
    @functools.wraps(fn)
    def wrapped(request, *args, **kwargs):
        if not request.user.has_perm('contests.contest_admin',
                request.contest):
            raise PermissionDenied
        return fn(request, *args, **kwargs)
    return wrapped
