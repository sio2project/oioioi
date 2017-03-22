import json

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.http import JsonResponse

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.base.admin import system_admin_menu_registry
from django.conf import settings
import xmlrpclib

server = xmlrpclib.ServerProxy(settings.SIOWORKERSD_URL, allow_none=True)


def get_info_about_workers():
    return server.get_workers()


def get_all_names():
    return [i['name'] for i in get_info_about_workers()]


def del_worker(l):
    for i in l:
        server.forget_worker(i)


@enforce_condition(is_superuser)
def show_info_about_workers(request):
    readonly = False
    announce = None
    delete = False
    if request.method == 'POST':
        if request.POST.get('delete'):
            readonly = True
            announce = _("""You are about to delete the selected workers.
                Please confirm""")
            delete = True
        if request.POST.get('confirm'):
            selected = [x for x in get_all_names() if
                request.POST.get("work-%s" % x)]
            del_worker(selected)
            announce = _("Successfully deleted selected workers")
    workers_info = get_info_about_workers()

    def transform_dict(d):
        select = request.POST.get('work-' + d['name'])
        info = d['info']
        result = {
            'name': d['name'],
            'ram': info.get('ram', '<unknown>'),
            'maxConcurr': info.get('concurrency', '<unknown>'),
            'select': select,
        }
        return result
    workers_info = map(transform_dict, workers_info)
    context = {
        'workers': workers_info,
        'readonly': readonly,
        'announce': announce,
        'delete': delete,
    }
    return render(request, 'workers/list_workers.html', context)


@enforce_condition(is_superuser)
def get_load_json(request):
    data = get_info_about_workers()
    capacity = 0
    load = 0
    for i in data:
        concurrency = int(i['info']['concurrency'])
        capacity += concurrency
        if bool(i['is_running_cpu_exec']):
            load += concurrency
        else:
            load += len(i['tasks'])
    return JsonResponse({'capacity': capacity, 'load': load})


system_admin_menu_registry.register('workers_management_admin',
        _("Manage workers"), lambda request:
        reverse('show_workers'),
        order=100)
