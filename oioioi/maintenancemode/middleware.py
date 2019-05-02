import re

from django.conf import settings
from django.http import HttpResponseRedirect

from oioioi.maintenancemode.models import is_maintenance_mode_enabled


class MaintenanceModeMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._process_request(request)

        if response is None:
            return self.get_response(request)

        return response

    def _process_request(self, request):
        if not is_maintenance_mode_enabled():
            return None

        # We want to allow admin access the site
        if hasattr(request, 'user'):
            if request.user.is_superuser:
                return None

        # If admin logged in as another user, the information who
        # the real user is is stored in real_user
        if hasattr(request, 'real_user'):
            if request.real_user.is_superuser:
                return None

        # Maybe we want to allow user access some links
        for url in settings.MAINTENANCE_MODE_IGNORE_URLS:
            if re.search(url, request.path_info):
                return None

        # We redirect users to the url specified in settings.
        return HttpResponseRedirect(settings.MAINTENANCE_MODE_REDIRECT_URL)
