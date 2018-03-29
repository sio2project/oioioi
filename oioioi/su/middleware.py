from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.shortcuts import redirect

from oioioi.su import SU_BACKEND_SESSION_KEY, SU_UID_SESSION_KEY
from oioioi.su.utils import get_user

REDIRECTION_AFTER_SU_KEY = "redirection_after_su"


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


class SuFirstTimeRedirectionMiddleware(object):
    """Middleware used for silent redirection on 403 after su'ing."""

    def process_exception(self, request, exception):
        if REDIRECTION_AFTER_SU_KEY in request.session:
            del request.session[REDIRECTION_AFTER_SU_KEY]

            if isinstance(exception, PermissionDenied):
                return redirect('index')

    def process_response(self, request, response):
        if REDIRECTION_AFTER_SU_KEY in request.session:
            if request.session[REDIRECTION_AFTER_SU_KEY] == 'PRE_SU':
                request.session[REDIRECTION_AFTER_SU_KEY] = 'POST_SU'
            else:
                del request.session[REDIRECTION_AFTER_SU_KEY]

        return response
