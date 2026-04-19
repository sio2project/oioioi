from django.db import models

from oioioi.base.utils import request_cached


class MaintenanceModeInfo(models.Model):
    """Represents maintenance state of the site. 'state'
    specifies if it's on or off. 'message' contains
    message to users (cause of the maintenance)
    """

    state = models.BooleanField(default=False)
    message = models.TextField(default="")


def get_maintenance_mode():
    info, _ = MaintenanceModeInfo.objects.get_or_create()
    return {"state": info.state, "message": info.message}


def set_maintenance_mode(new_state, new_message=""):
    MaintenanceModeInfo.objects.update_or_create({"state": new_state, "message": new_message})


def _is_maintenance_mode_enabled():
    info, _ = MaintenanceModeInfo.objects.get_or_create()
    return info.state


@request_cached
def _is_maintenance_mode_enabled_cached(request):
    return _is_maintenance_mode_enabled()


def is_maintenance_mode_enabled(request=None):
    if request is None:
        return _is_maintenance_mode_enabled()
    return _is_maintenance_mode_enabled_cached(request)
