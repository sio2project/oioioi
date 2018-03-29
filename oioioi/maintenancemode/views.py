from django.http import HttpResponseRedirect
from django.shortcuts import render

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.maintenancemode.models import (get_maintenance_mode,
                                           is_maintenance_mode_enabled,
                                           set_maintenance_mode)


def maintenance_view(request):
    # We don't want users to access maintenance site
    # when maintenance is disabled.
    if not is_maintenance_mode_enabled():
        return HttpResponseRedirect('/')
    maintenance_info = get_maintenance_mode()
    return render(request, 'maintenance.html',
                  {'message': maintenance_info['message']})


@enforce_condition(is_superuser)
def set_maintenance_mode_view(request):
    if request.method == 'POST':
        if 'set_button' in request.POST:
            message = request.POST['message']
            set_maintenance_mode(True, message)
        elif 'turn_off_button' in request.POST:
            set_maintenance_mode(False)

    maintenance_info = get_maintenance_mode()
    return render(request, 'set_maintenance.html',
                  {
                      'message': maintenance_info['message'],
                      'state': maintenance_info['state'],
                  })
