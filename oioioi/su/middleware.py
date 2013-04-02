from django.core.exceptions import ImproperlyConfigured

from oioioi.su import SU_BACKEND_SESSION_KEY, SU_UID_SESSION_KEY
from oioioi.su.utils import get_user


class SuAuthenticationMiddleware(object):
    """Middleware overriding current request.user object with that switched to.

       User object representing real user privileges are stored in
       ``request.real_user``.
    """

    def process_request(self, request):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The SuAuthenticationMiddleware requires the"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")

        request.real_user = request.user
        if SU_UID_SESSION_KEY in request.session:
            request.user = get_user(request,
                    request.session[SU_UID_SESSION_KEY],
                    request.session[SU_BACKEND_SESSION_KEY])
