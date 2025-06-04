from django.conf import settings
from django.utils.functional import lazy
from django.utils.module_loading import import_string
from django.db.models import Q

from oioioi.base.utils import request_cached
from oioioi.base.utils.query_helpers import Q_always_false
from oioioi.contests.models import Contest, ContestView
from oioioi.contests.utils import visible_contests, visible_contests_queryset
from oioioi.contests.utils import used_controllers

def register_current_contest(request):
    """A template context processor which makes the current contest available
    to the templates.

    The current :class:`~oioioi.contests.models.Contest` instance is added
    to the template context as a ``contest`` variable.

    Must be used together with
    :class:`~oioioi.contests.middleware.CurrentContestMiddleware`.
    """
    if hasattr(request, 'contest'):
        return {'contest': request.contest}
    else:
        return {}


@request_cached
def recent_contests(request):
    if request.real_user.is_anonymous:
        ids = request.session.get('recent_contests', [])
        mapping = Contest.objects.in_bulk(ids)
        return [
            c
            for c in (mapping.get(id) for id in ids)
            if c is not None and c != request.contest
        ]
    else:
        c_views = ContestView.objects.filter(user=request.real_user).select_related(
            'contest'
        )
        c_views = c_views[: getattr(settings, 'NUM_RECENT_CONTESTS', 5)]
        return [cv.contest for cv in c_views if cv.contest in visible_contests(request)]


def register_recent_contests(request):
    if not hasattr(request, 'contest') or not hasattr(request, 'session'):
        return {}

    def generator():
        return recent_contests(request)

    return {'recent_contests': lazy(generator, list)()}
