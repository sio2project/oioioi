from django.core.urlresolvers import reverse

from oioioi.base.permissions import is_superuser
from oioioi.status import status_registry


def get_status(request):
    """Returns dict composed by ``status_registry`` functions."""
    response = {
        'is_superuser': is_superuser(request),
        'user': request.user.username,
        'sync_time': 300000,  # in ms
    }
    if getattr(request, 'contest', None) is not None:
        response['contest_id'] = request.contest.id
        response['status_url'] = reverse('get_contest_status',
                kwargs={'contest_id': request.contest.id})
    else:
        response['status_url'] = reverse('get_status')

    # FIXME: Django doesn't load all 'views.py' in some cases, which may cause
    # FIXME: status_registry being not yet populated
    for fun in status_registry:
        response = fun(request, response)

    return response
