from django.contrib.auth.models import AnonymousUser

from oioioi.su.utils import is_under_su


def real_user(request):
    if not hasattr(request, 'real_user'):
        return {
            'real_user': getattr(request, 'user', AnonymousUser()),
            'is_under_su': False,
        }
    else:
        return {'real_user': request.real_user, 'is_under_su': is_under_su(request)}
