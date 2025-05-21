from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse

from oioioi.participants.models import OnsiteRegistration
from oioioi.su.utils import is_under_su, reset_to_real_user


# Code based on django.contrib.auth.middleware.RemoteUserMiddleware
class IpDnsAuthMiddleware(object):
    """Middleware for authentication based on user IP or DNS hostname."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)

        return self.get_response(request)

    def _process_request(self, request):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The IpDns user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the IpDnsAuthMiddleware class."
            )

        ip_addr = request.META.get('REMOTE_ADDR')
        dns_name = request.META.get('REMOTE_HOST')

        if dns_name == ip_addr:
            dns_name = None

        if not dns_name and not ip_addr:
            return

        user = auth.authenticate(request, ip_addr=ip_addr, dns_name=dns_name)
        if user and (not request.user.is_authenticated or request.user != user):
            auth.login(request, user)


# Code based on django.contrib.auth.middleware.RemoteUserMiddleware
class ForceDnsIpAuthMiddleware(object):
    """Middleware which allows only IP/DNS login for participants of
    on-site contests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " earlier in MIDDLEWARE."
            )
        if not request.user.is_anonymous and not hasattr(request.user, 'backend'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.base.middleware.AnnotateUserBackendMiddleware'"
                " earlier in MIDDLEWARE."
            )
        if not hasattr(request, 'contest'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.contests.middleware.CurrentContestMiddleware'"
                " earlier in MIDDLEWARE."
            )
        if not request.contest:
            return
        if not hasattr(request, 'contest_exclusive'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.contextexcl.middleware.ExclusiveContestsMiddleware'"
                " earlier in MIDDLEWARE."
            )
        if not request.contest_exclusive:
            return
        if not request.contest.controller.is_onsite():
            return
        if not request.user.is_authenticated:
            return
        if not OnsiteRegistration.objects.filter(
            participant__user_id=request.user.id,
            participant__contest=request.contest,
            region__isnull=False,
        ).exists():
            return
        backend_path = request.user.backend
        if backend_path != 'oioioi.ipdnsauth.backends.IpDnsBackend':
            if is_under_su(request):
                reset_to_real_user(request)
            else:
                auth.logout(request)
            return TemplateResponse(
                request, 'ipdnsauth/access_blocked.html', {'auth_backend': backend_path}
            )
