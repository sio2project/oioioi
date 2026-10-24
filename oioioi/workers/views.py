import xmlrpc.client
from operator import itemgetter  # pylint: disable=E0611

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from oioioi.base.admin import system_admin_menu_registry
from oioioi.base.permissions import enforce_condition, is_superuser

server = xmlrpc.client.ServerProxy(settings.SIOWORKERSD_URL, allow_none=True)

# Errors meaning that sioworkersd can't be reached. An xmlrpc.client.Fault
# is different: it is an error reported by a running sioworkersd.
UNAVAILABLE_ERRORS = (OSError, xmlrpc.client.ProtocolError)
SERVICE_ERRORS = (*UNAVAILABLE_ERRORS, xmlrpc.client.Fault)

UNAVAILABLE_MESSAGE = _("The workers service is unavailable. Check that sioworkersd is running and try again.")
FAULT_MESSAGE = _("The workers service returned an error: %(error)s")


def get_info_about_workers():
    return server.get_workers()


def get_all_names():
    return [i["name"] for i in get_info_about_workers()]


def del_worker(value):
    """Forgets the given workers. Returns a list of (name, fault string)
    pairs for the workers that sioworkersd refused to forget.
    """
    failed = []
    for i in value:
        try:
            server.forget_worker(i)
        except xmlrpc.client.Fault as e:
            failed.append((i, e.faultString))
    return failed


def service_error_message(error):
    if isinstance(error, xmlrpc.client.Fault):
        return FAULT_MESSAGE % {"error": error.faultString}
    return UNAVAILABLE_MESSAGE


def delete_selected_workers(request):
    """Deletes the workers selected in the form. Returns a pair
    (announce, error), one of which is None.
    """
    try:
        selected = [x for x in get_all_names() if request.POST.get(f"work-{x}")]
        failed = del_worker(selected)
    except SERVICE_ERRORS as e:
        return None, service_error_message(e)
    if failed:
        return None, _("Could not delete some workers: %(failed)s") % {"failed": "; ".join(f"{name} ({error})" for name, error in failed)}
    return _("Successfully deleted selected workers"), None


@enforce_condition(is_superuser)
def show_info_about_workers(request):
    readonly = False
    announce = None
    warning = None
    connection_error = None
    delete_error = None
    delete = False
    if request.method == "POST":
        if request.POST.get("delete"):
            readonly = True
            announce = _(
                """You are about to delete the selected workers.
                Please confirm"""
            )
            delete = True
        if request.POST.get("confirm"):
            announce, delete_error = delete_selected_workers(request)
    try:
        workers_info = get_info_about_workers()
    except SERVICE_ERRORS as e:
        workers_info = []
        connection_error = service_error_message(e)

    def transform_dict(d):
        select = request.POST.get("work-" + d["name"])
        info = d["info"]
        result = {
            "name": d["name"],
            "ram": info.get("available_ram_mb", "<unknown>"),
            "concurrency": info["concurrency"],
            "can_run_cpu_exec": info["can_run_cpu_exec"],
            "select": select,
        }
        return result

    workers_info = list(map(transform_dict, workers_info))

    if not any(map(itemgetter("can_run_cpu_exec"), workers_info)) and not settings.USE_UNSAFE_EXEC:
        warning = _("There aren't any workers allowed to run cpu-exec jobs.")

    context = {
        "workers": workers_info,
        "readonly": readonly,
        "announce": announce,
        "warning": warning,
        "connection_error": connection_error,
        "delete_error": delete_error,
        "delete": delete,
    }
    return render(request, "workers/list_workers.html", context)


@enforce_condition(is_superuser)
def get_load_json(request):
    try:
        data = get_info_about_workers()
    except UNAVAILABLE_ERRORS:
        return JsonResponse(
            {"error": gettext("The workers service is unavailable.")},
            status=503,
        )
    except xmlrpc.client.Fault as e:
        return JsonResponse(
            {"error": service_error_message(e)},
            status=502,
        )
    capacity = 0
    load = 0
    cpu_exec_load = 0
    for i in data:
        concurrency = int(i["info"]["concurrency"])
        capacity += concurrency
        if bool(i["is_running_cpu_exec"]):
            load += concurrency
            cpu_exec_load += concurrency
        else:
            load += len(i["tasks"])
    return JsonResponse({"capacity": capacity, "load": load, "cpu_exec_load": cpu_exec_load})


system_admin_menu_registry.register(
    "workers_management_admin",
    _("Manage workers"),
    lambda request: reverse("show_workers"),
    order=100,
)
