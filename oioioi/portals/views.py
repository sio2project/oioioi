from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.db import IntegrityError
from mptt.exceptions import InvalidMove
from oioioi.base.menu import account_menu_registry
from oioioi.portals.models import Node, Portal
from oioioi.portals.forms import NodeForm
from oioioi.portals.actions import node_actions, portal_actions, \
        register_node_action, register_portal_action, portal_url, \
        DEFAULT_ACTION_NAME
from oioioi.portals.utils import resolve_path, is_portal_admin, \
        current_node_is_root
from oioioi.portals.widgets import render_panel


def create_portal_view(request, username):
    if username != request.user.username:
        raise PermissionDenied

    if Portal.objects.filter(owner__username=username).exists():
        raise Http404

    if request.method != 'POST':
        return render(request, 'portals/create-portal.html')
    else:
        if 'confirmation' in request.POST:
            name = render_to_string(
                    'portals/initial-main-page-name.txt')
            body = render_to_string(
                    'portals/initial-main-page-body.txt')
            root = Node.objects.create(full_name=name, short_name='',
                                       parent=None, panel_code=body)
            portal = Portal.objects.create(owner=request.user,
                                           root=root)
            return redirect(portal_url(portal=portal))
        else:
            return redirect('/')


def portal_view(request, username, portal_path):
    if 'action' in request.GET:
        action = request.GET['action']
    else:
        action = DEFAULT_ACTION_NAME

    request.portal = get_object_or_404(Portal, owner__username=username)
    request.action = action

    if action in node_actions:
        request.current_node = resolve_path(request.portal, portal_path)
        view = node_actions[action]
    elif action in portal_actions:
        view = portal_actions[action]
    else:
        raise Http404

    return view(request)


@register_node_action('show_node', menu_text=_("Show node"), menu_order=100)
def show_node_view(request):
    rendered_panel = mark_safe(render_panel(request.current_node.panel_code))
    return render(request, 'portals/show-node.html',
                  {'rendered_panel': rendered_panel})


@register_node_action('edit_node', condition=is_portal_admin,
                      menu_text=_("Edit node"), menu_order=200)
def edit_node_view(request):
    if request.method != 'POST':
        form = NodeForm(instance=request.current_node)
    else:
        form = NodeForm(request.POST, instance=request.current_node)
        if form.is_valid():
            node = form.save()
            return redirect(portal_url(node=node))

    return render(request, 'portals/edit-node.html', {'form': form})


@register_node_action('add_node', condition=is_portal_admin,
                      menu_text=_("Add child node"), menu_order=300)
def add_node_view(request):
    if request.method != 'POST':
        form = NodeForm(initial={'parent': request.current_node})
    else:
        instance = Node(parent=request.current_node)
        form = NodeForm(request.POST, instance=instance)
        if form.is_valid():
            node = form.save()
            return redirect(portal_url(node=node))

    return render(request, 'portals/add-node.html', {'form': form})


@register_node_action('delete_node',
                      condition=is_portal_admin & ~current_node_is_root,
                      menu_text=_("Delete node"), menu_order=400)
def delete_node_view(request):
    if request.method != 'POST':
        return render(request, 'portals/delete-node.html')
    else:
        if 'confirmation' in request.POST:
            parent = request.current_node.parent
            request.current_node.delete()
            return redirect(portal_url(node=parent))
        else:
            return redirect(portal_url(node=request.current_node))


@register_portal_action('manage_portal', condition=is_portal_admin,
                        menu_text=_("Manage portal"), menu_order=500)
def manage_portal_view(request):
    return render(request, 'portals/manage-portal.html')


@register_portal_action('portal_tree_json', condition=is_portal_admin)
def portal_tree_json_view(request):
    nodes = request.portal.root.get_descendants(include_self=True)
    json = render_to_string('portals/portal-tree.json', {'nodes': nodes})
    json = json.replace('}{', '},{')
    return HttpResponse(json)


def move_node_view(request):
    position_mapping = {'before': 'left', 'after': 'right',
                        'inside': 'first-child'}
    position = request.GET['position']
    if position not in position_mapping:
        raise SuspiciousOperation
    position = position_mapping[position]

    try:
        target = Node.objects.get(pk=request.GET['target'])
    except Node.DoesNotExist:
        raise SuspiciousOperation
    target_portal = target.get_root().portal

    request.portal = target_portal
    if not is_portal_admin(request):
        raise SuspiciousOperation
    if position != 'first-child' and target.is_root_node():
        raise SuspiciousOperation

    try:
        node = Node.objects.get(pk=request.GET['node'])
    except Node.DoesNotExist:
        raise SuspiciousOperation
    if node.get_root().portal != target_portal:
        raise SuspiciousOperation

    try:
        node.move_to(target, position)
    except (InvalidMove, IntegrityError):
        raise SuspiciousOperation

    return HttpResponse()


@register_portal_action('delete_portal', condition=is_portal_admin)
def delete_portal_view(request):
    if request.method != 'POST':
        return render(request, 'portals/delete-portal.html')
    else:
        if 'confirmation' in request.POST:
            request.portal.root.delete()
            request.portal.delete()
            return redirect('/')
        else:
            return redirect(portal_url(portal=request.portal,
                                       action='manage_portal'))


def my_portal_url(request):
    try:
        return portal_url(portal=request.user.portal)
    except Portal.DoesNotExist:
        return reverse('create_portal',
                       kwargs={'username': request.user.username})

account_menu_registry.register('my_portal', _("My portal"), my_portal_url,
        order=150)
