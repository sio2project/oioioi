from django.http import HttpResponseRedirect
from django.conf import settings

import re

from oioioi.maintenancemode.models import is_maintenance_mode_enabled


class MaintenanceModeMiddleware(object):

    def process_request(self, request):
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
