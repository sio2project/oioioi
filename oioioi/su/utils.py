from django.contrib import auth
from django.conf import settings

from oioioi.base.permissions import is_superuser, make_request_condition
from oioioi.contests.utils import is_contest_basicadmin, contest_exists
from oioioi.su import SU_BACKEND_SESSION_KEY, SU_UID_SESSION_KEY, SU_REAL_USER_IS_SUPERUSER, SU_ORIGINAL_CONTEST


@make_request_condition
def is_real_superuser(request):
    if hasattr(request, 'real_user'):
        return request.real_user.is_superuser
    else:
        return is_superuser(request)


@make_request_condition
def is_under_su(request):
    return SU_UID_SESSION_KEY in request.session


@make_request_condition
def can_contest_admins_su(_):
    return getattr(settings, 'CONTEST_ADMINS_CAN_SU', False)


def get_user(request, user_id, backend_path):
    backend = auth.load_backend(backend_path)
    user = backend.get_user(user_id)
    user.backend = backend_path
    return user


def su_to_user(request, user, backend_path=None):
    """Changes current *effective* user to ``user``.

    After changing to ``user``, original ``request.user`` is saved in
    ``request.real_user``.
    If given, ``backend_path`` should be dotted name of authentication
    backend, otherwise it's inherited from current user.
    """
    if not backend_path:
        backend_path = request.user.backend

    request.session[SU_UID_SESSION_KEY] = user.id
    request.session[SU_BACKEND_SESSION_KEY] = backend_path
    request.session[SU_REAL_USER_IS_SUPERUSER] = is_superuser(request)
    if not is_superuser(request) and contest_exists(request) and is_contest_basicadmin(request):
        request.session[SU_ORIGINAL_CONTEST] = request.contest.id

    request.real_user = request.user
    request.user = get_user(request, user.id, backend_path)


def reset_to_real_user(request):
    """Changes *effective* user back to *real* user"""
    request.user = request.real_user

    del request.session[SU_UID_SESSION_KEY]
    del request.session[SU_BACKEND_SESSION_KEY]
    if SU_REAL_USER_IS_SUPERUSER in request.session:
        del request.session[SU_REAL_USER_IS_SUPERUSER]
    if SU_ORIGINAL_CONTEST in request.session:
        del request.session[SU_ORIGINAL_CONTEST]
