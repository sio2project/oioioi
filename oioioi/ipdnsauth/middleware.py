from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse

from oioioi.su.utils import is_under_su, reset_to_real_user


# Code based on django.contrib.auth.middleware.RemoteUserMiddleware
class IpDnsAuthMiddleware(object):
    """Middleware for authentication based on user IP or DNS hostname."""

    def process_request(self, request):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The IpDns user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the IpDnsAuthMiddleware class.")

        ip_addr = request.META.get('REMOTE_ADDR')
        dns_name = request.META.get('REMOTE_HOST')

        if dns_name == ip_addr:
            dns_name = None

        if not dns_name and not ip_addr:
            return

        user = auth.authenticate(ip_addr=ip_addr, dns_name=dns_name)
        if user:
            auth.login(request, user)


# Code based on django.contrib.auth.middleware.RemoteUserMiddleware
class ForceDnsIpAuthMiddleware(object):
    """Middleware which allows only IP/DNS login for participants of
       on-site contests."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not request.user.is_anonymous and \
                not hasattr(request.user, 'backend'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.base.middleware.AnnotateUserBackendMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not hasattr(request, 'contest'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.contests.middleware.CurrentContestMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not request.contest:
            return
        if not hasattr(request, 'contest_exclusive'):
            raise ImproperlyConfigured(
                "The ForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.contextexcl.middleware.ExclusiveContestsMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not request.contest_exclusive:
            return
        if not request.contest.controller.is_onsite():
            return
        if not request.user.is_authenticated:
            return
        backend_path = request.user.backend
        if backend_path != 'oioioi.ipdnsauth.backends.IpDnsBackend':
            if is_under_su(request):
                reset_to_real_user(request)
            else:
                auth.logout(request)
            return TemplateResponse(request, 'ipdnsauth/access_blocked.html',
                                    {'auth_backend': backend_path})
