from django.conf import settings
from django.utils.functional import lazy
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

def recent_contests(request):
    ids = request.session.get('recent_contests', [])
    mapping = Contest.objects.in_bulk(ids)
    return filter(lambda c: c is not None and c != request.contest,
            [mapping.get(id) for id in ids])

def register_recent_contests(request):
    if not hasattr(request, 'contest') or not hasattr(request, 'session'):
        return {}
    def generator():
        return recent_contests(request)
    return {'recent_contests': lazy(generator, list)()}

def register_only_default_contest(request):
    return {'only_default_contest': getattr(settings,'ONLY_DEFAULT_CONTEST',
        False)}
