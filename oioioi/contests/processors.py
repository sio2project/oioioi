from django.utils.functional import lazy
from oioioi.base.utils import request_cached
from oioioi.contests.models import Contest

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
    ids = request.session.get('recent_contests', [])
    mapping = Contest.objects.in_bulk(ids)
    return [c for c in (mapping.get(id) for id in ids)
            if c is not None and c != request.contest]


def register_recent_contests(request):
    if not hasattr(request, 'contest') or not hasattr(request, 'session'):
        return {}
    def generator():
        return recent_contests(request)
    return {'recent_contests': lazy(generator, list)()}

