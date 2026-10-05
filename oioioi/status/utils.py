from django.urls import reverse

from oioioi.base.permissions import is_superuser
from oioioi.status.registry import status_registry


def get_status(request):
    """Returns dict composed by ``status_registry`` functions."""
    response = {
        "is_superuser": is_superuser(request),
        "user": request.user.username,
        "sync_time": 300000,  # in ms
        "status_url": reverse("get_status"),
    }
    if getattr(request, "contest", None) is not None:
        response["contest_id"] = request.contest.id

    # FIXME: Django doesn't load all 'views.py' in some cases, which may cause
    # FIXME: status_registry being not yet populated
    for fun in status_registry:
        response = fun(request, response)

    return response
