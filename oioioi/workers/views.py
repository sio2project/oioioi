import json

from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.base.admin import system_admin_menu_registry


#TODO dummy function -- should be filled when the server is able to response
def get_info_about_workers():
    workers_info = [("Komp%d" % j, j, 2 ** j,
        ["tag%d" % (i + j) for i in range(100)]) for j in range(6)]
    return workers_info


#TODO dummy function -- should be filled when the server is able to response
def get_all_tags():
    answer = ["tag%d" % i for i in range(106)]
    return answer


#TODO dummy function -- should be filled when the server is able to response
def get_all_names():
    answer = ["Komp%d" % j for j in range(6)]
    return answer


#TODO dummy function -- should be filled when the server is able to response
def del_worker(l):
    return 0


#TODO dummy function -- should be filled when the server is able to response
def del_tag_from_workers(t, l):
    return 0


#TODO dummy function -- should be filled when the server is able to response
def add_tag_to_workers(t, l):
    return 0


@enforce_condition(is_superuser)
def show_info_about_workers(request):
    readonly = False
    announce = None
    error = None
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
            ret = del_worker(selected)
            if ret == 0:
                announce = _("Successfully deleted selected workers")
            else:
                error = _("Error %d when deleting workers") % ret
        if request.POST.get('tagadd'):
            tag_name = request.POST.get('tagname')
            selected = [x for x in get_all_names() if
                request.POST.get('work-%s' % x)]
            ret = add_tag_to_workers(tag_name, selected)
            if ret == 0:
                announce = _("Successfully added tag")
            else:
                error = _("Error %d when adding tag") % ret
        if request.POST.get('tagdelete'):
            selected = [x for x in get_all_names() if
                request.POST.get('work-%s' % x)]
            tag_name = request.POST.get('tagname')
            ret = del_tag_from_workers(tag_name, selected)
            if ret == 0:
                announce = _("Successfully deleted tag")
            else:
                error = _("Error %d when deleting tag") % ret
    workers_info = get_info_about_workers()

    def tuple_to_dict(tup):
        select = request.POST.get('work-' + tup[0])
        result = {
            'name': tup[0],
            'ram': tup[1],
            'maxConcurr': tup[2],
            'tags': tup[3],
            'select': select,
        }
        return result
    workers_info = map(tuple_to_dict, workers_info)
    context = {
        'workers': workers_info,
        'readonly': readonly,
        'announce': announce,
        'error': error,
        'edit': edit,
        'delete': delete,
        'all_tags': all_tags
    }
    return render(request, 'workers/list_workers.html', context)

system_admin_menu_registry.register('workers_management_admin',
        _("Manage workers"), lambda request:
        reverse('show_workers'),
        order=100)
