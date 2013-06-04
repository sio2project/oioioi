from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.template.response import TemplateResponse
from oioioi.oi.controllers import OIOnsiteContestController
from oioioi.participants.models import Participant


# Code based on django.contrib.auth.middleware.RemoteUserMiddleware
class OiForceDnsIpAuthMiddleware(object):
    """Middleware which allows only IP/DNS login for participants for
       contests with OIOnsiteContestControllers."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The OiForceDnsIpAuthMiddleware middleware requires the"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not request.user.is_anonymous() and \
                not hasattr(request.user, 'backend'):
            raise ImproperlyConfigured(
                "The OiForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.base.middleware.AnnotateUserBackendMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not hasattr(request, 'contest'):
            raise ImproperlyConfigured(
                "The OiForceDnsIpAuthMiddleware middleware requires the"
                " 'oioioi.contests.middleware.CurrentContestMiddleware'"
                " earlier in MIDDLEWARE_CLASSES.")
        if not request.contest:
            return
        if not isinstance(request.contest.controller,
                OIOnsiteContestController):
            return
        if not request.user.is_authenticated():
            return
        if request.user.has_perm('contests.contest_admin', request.contest):
            return
        if not Participant.objects.filter(user=request.user,
                contest=request.contest, status='ACTIVE'):
            return
        backend_path = request.user.backend
        if backend_path != 'oioioi.ipdnsauth.backends.IpDnsBackend':
            auth.logout(request)
            return TemplateResponse(request, 'oi/access_blocked.html',
                {'auth_backend': backend_path})
