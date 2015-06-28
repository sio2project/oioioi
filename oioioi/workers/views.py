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


def get_all_tags():
    return server.list_tags()


def get_all_names():
    return [i['name'] for i in get_info_about_workers()]


def del_worker(l):
    for i in l:
        server.forget_worker(i)


def del_tag_from_workers(tag, l):
    server.del_tag(l, tag)


def add_tag_to_workers(tag, l):
    server.add_tag(l, tag)


@enforce_condition(is_superuser)
def show_info_about_workers(request):
    readonly = False
    announce = None
    edit = False
    delete = False
    all_tags = None
    if request.method == 'POST':
        if request.POST.get('edit'):
            readonly = True
            announce = _("Select tag to add or remove from selected workers")
            edit = True
            all_tags = json.dumps(get_all_tags())
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
        if request.POST.get('tagadd'):
            tag_name = request.POST.get('tagname')
            selected = [x for x in get_all_names() if
                request.POST.get('work-%s' % x)]
            add_tag_to_workers(tag_name, selected)
            announce = _("Successfully added tag")
        if request.POST.get('tagdelete'):
            selected = [x for x in get_all_names() if
                request.POST.get('work-%s' % x)]
            tag_name = request.POST.get('tagname')
            del_tag_from_workers(tag_name, selected)
            announce = _("Successfully deleted tag")
    workers_info = get_info_about_workers()

    def transform_dict(d):
        select = request.POST.get('work-' + d['name'])
        info = d['info']
        result = {
            'name': d['name'],
            'ram': info.get('ram', '<unknown>'),
            'maxConcurr': info.get('concurrency', '<unknown>'),
            'tags': d['tags'],
            'select': select,
        }
        return result
    workers_info = map(transform_dict, workers_info)
    context = {
        'workers': workers_info,
        'readonly': readonly,
        'announce': announce,
        'edit': edit,
        'delete': delete,
        'all_tags': all_tags
    }
    return render(request, 'workers/list_workers.html', context)


@enforce_condition(is_superuser)
def get_load_json(request):
    data = get_info_about_workers()
    cap = 0
    load = 0
    for i in data:
        cap += min(1, i['info'].get('concurrency', 1))
        load += len(i['tasks'])
    return JsonResponse({'capacity': cap, 'load': load})


system_admin_menu_registry.register('workers_management_admin',
        _("Manage workers"), lambda request:
        reverse('show_workers'),
        order=100)
