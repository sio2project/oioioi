from django.conf import settings
from django.template import Library, RequestContext

from oioioi.contests.processors import recent_contests
from oioioi.contests.utils import visible_contests
from oioioi.teachers.models import Teacher

register = Library()


@register.inclusion_tag("teachers/contest-selection.html", takes_context=True)
def contest_selection(context):
    request = context["request"]
    to_show = getattr(settings, "NUM_RECENT_CONTESTS", 5)

    rcontests = recent_contests(request)
    contests = list(visible_contests(request).difference(rcontests))
    contests.sort(key=lambda x: x.creation_date, reverse=True)
    contests = (rcontests + contests)[: to_show + 1]

    default_contest = None
    if rcontests:
        default_contest = rcontests[0]
    elif contests:
        default_contest = contests[0]

    contest_selection_context = {
        "contests": contests[:to_show],
        "default_contest": default_contest,
        "more_contests": len(contests) > to_show,
        "is_teacher": request.user.has_perm("teachers.teacher"),
        "is_inactive_teacher": request.user.is_authenticated and bool(Teacher.objects.filter(user=request.user, is_active=False)),
    }
    return RequestContext(request, contest_selection_context)
