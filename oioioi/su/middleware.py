from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http.response import HttpResponseForbidden
from django.shortcuts import redirect
from django.conf import settings
from django.urls import resolve

from oioioi.base.utils.middleware import was_response_generated_by_exception
from oioioi.contests.current_contest import contest_re
from oioioi.su import (
    SU_BACKEND_SESSION_KEY,
    SU_UID_SESSION_KEY,
    SU_REAL_USER_IS_SUPERUSER,
    SU_ORIGINAL_CONTEST,
    BLOCKED_URL_NAMESPACES,
    BLOCKED_URLS
)
from oioioi.su.utils import get_user, reset_to_real_user

REDIRECTION_AFTER_SU_KEY = "redirection_after_su"


class SuAuthenticationMiddleware(object):
    """Middleware overriding current request.user object with that switched to.

    User object representing real user privileges are stored in
    ``request.real_user``.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._process_request(request)
        if response:
            return response

        return self.get_response(request)

    def _process_request(self, request):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The SuAuthenticationMiddleware requires the"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " earlier in MIDDLEWARE."
            )

        request.real_user = request.user
        if SU_UID_SESSION_KEY in request.session:
            request.user = get_user(
                request,
                request.session[SU_UID_SESSION_KEY],
                request.session[SU_BACKEND_SESSION_KEY],
            )
            # Check if the user is contest admin.
            if not request.session.get(SU_REAL_USER_IS_SUPERUSER, True):
                # Might happen when switching to a user which then becomes a superuser.
                if request.user.is_superuser:
                    reset_to_real_user(request)
                    return redirect('index')

                original_contest_id = request.session.get(SU_ORIGINAL_CONTEST)
                contest_id = None
                m = contest_re.match(request.path)
                if m is not None:
                    contest_id = m.group('c_name')
                url = resolve(request.path_info)
                is_su_reset_url = url.url_name == 'su_reset'
                nonoioioi_namespace = url.namespaces == []
                for ns in url.namespaces:
                    if ns != 'contest' and ns != 'noncontest':
                        nonoioioi_namespace = True
                        break
                # Redirect if the url is not in the same contest, is not a su reset url and is an url made by oioioi.
                # For example, `nonoioioi_namespace` can be True when the url is /jsi18n/
                if (
                    not is_su_reset_url and
                    not nonoioioi_namespace and
                    (contest_id is None or contest_id != original_contest_id)
                ):
                    return redirect('su_url_not_allowed', contest_id=original_contest_id)

                for ns in url.namespaces:
                    if ns in BLOCKED_URL_NAMESPACES:
                        return redirect('su_url_not_allowed', contest_id=original_contest_id)
                if url.url_name in BLOCKED_URLS:
                    return redirect('su_url_not_allowed', contest_id=original_contest_id)

                if (
                    not is_su_reset_url and
                    getattr(settings, 'ALLOW_ONLY_GET_FOR_SU_CONTEST_ADMINS', True) and request.method != 'GET'
                ):
                    return redirect('su_method_not_allowed', contest_id=original_contest_id)


class SuFirstTimeRedirectionMiddleware(object):
    """Middleware used for silent redirection on 403 after su'ing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return self._process_response(request, response)

    def process_exception(self, request, exception):
        if REDIRECTION_AFTER_SU_KEY in request.session:
            del request.session[REDIRECTION_AFTER_SU_KEY]

            if isinstance(exception, PermissionDenied):
                return redirect('index')

    def _process_response(self, request, response):
        if REDIRECTION_AFTER_SU_KEY in request.session:
            if was_response_generated_by_exception(response):
                del request.session[REDIRECTION_AFTER_SU_KEY]

                if isinstance(response, HttpResponseForbidden):
                    return redirect('index')

            elif request.session[REDIRECTION_AFTER_SU_KEY] == 'PRE_SU':
                request.session[REDIRECTION_AFTER_SU_KEY] = 'POST_SU'

            else:
                del request.session[REDIRECTION_AFTER_SU_KEY]

        return response
