from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from mptt.exceptions import InvalidMove
from oioioi.base.menu import account_menu_registry
from oioioi.portals.models import Node, Portal
from oioioi.portals.forms import NodeForm
from oioioi.portals.utils import can_edit_portal, get_node_context, \
        get_edit_node_context, join_paths, parent_path, portal_url


def portal_view(request, username, portal_path):
    if 'action' in request.GET:
        action = request.GET['action']
    else:
        action = 'show'

    if action in ('show', 'edit', 'add', 'delete'):
        view = globals()[action + '_node_view']
        return view(request, username, portal_path)
    elif action in ('manage_portal', 'delete_portal', 'portal_tree_json'):
        view = globals()[action + '_view']
        return view(request, username)
    else:
        raise Http404


def show_node_view(request, username, portal_path):
    if username == request.user.username:
        try:
            request.user.portal
        except Portal.DoesNotExist:
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
                    Portal.objects.create(owner=request.user, root=root)
                    return redirect(portal_url(username))
                else:
                    return redirect('/')

    return render(request, 'portals/show-node.html',
                  get_node_context(request, username, portal_path))


account_menu_registry.register('my_portal', _("My portal"),
        lambda request:
            portal_url(request.user.username),
        order=150)


def edit_node_view(request, username, portal_path):
    context = get_edit_node_context(request, username, portal_path)

    if request.method != 'POST':
        form = NodeForm(instance=context['node'])
    else:
        form = NodeForm(request.POST, instance=context['node'])
        if form.is_valid():
            node = form.save()
            return redirect(portal_url(username,
                                       join_paths(parent_path(portal_path),
                                                  node.short_name),
                                       'edit'))

    context['form'] = form
    return render(request, 'portals/edit-node.html', context)


def add_node_view(request, username, portal_path):
    context = get_edit_node_context(request, username, portal_path)

    if request.method != 'POST':
        form = NodeForm(initial={'parent': context['node']})
    else:
        instance = Node(parent=context['node'])
        form = NodeForm(request.POST, instance=instance)
        if form.is_valid():
            node = form.save()
            return redirect(portal_url(username,
                                       join_paths(portal_path,
                                                  node.short_name),
                                       'edit'))

    context['form'] = form
    return render(request, 'portals/add-node.html', context)


def delete_node_view(request, username, portal_path):
    context = get_edit_node_context(request, username, portal_path)
    if context['node'].is_root_node():
        raise Http404

    if request.method != 'POST':
        return render(request, 'portals/delete-node.html', context)
    else:
        if 'confirmation' in request.POST:
            context['node'].delete()
            return redirect(portal_url(username,
                                       parent_path(context['portal_path'])))
        else:
            return redirect(portal_url(username, context['portal_path']))


def manage_portal_view(request, username):
    owner = get_object_or_404(User, username=username)
    portal = get_object_or_404(Portal, owner=owner)

    if not can_edit_portal(request.user, portal):
        raise PermissionDenied

    return render(request, 'portals/manage-portal.html', {'owner': owner})


def portal_tree_json_view(request, username):
    portal = get_object_or_404(Portal, owner__username=username)

    if not can_edit_portal(request.user, portal):
        raise PermissionDenied

    nodes = portal.root.get_descendants(include_self=True)
    json = render_to_string('portals/portal-tree.json', {'nodes': nodes})
    json = json.replace('}{', '},{')
    return HttpResponse(json)


def move_node_view(request):
    position_mapping = {'before': 'left', 'after': 'right',
                        'inside': 'first-child'}
    position = request.GET['position']
    if position not in position_mapping:
        raise Http404
    position = position_mapping[position]

    target = get_object_or_404(Node, pk=request.GET['target'])
    target_portal = target.get_root().portal

    if not can_edit_portal(request.user, target_portal):
        raise PermissionDenied
    if position != 'first-child' and target.is_root_node():
        raise Http404

    node = get_object_or_404(Node, pk=request.GET['node'])
    if node.get_root().portal != target_portal:
        raise PermissionDenied

    try:
        node.move_to(target, position)
    except InvalidMove:
        raise Http404

    return HttpResponse()


def delete_portal_view(request, username):
    portal = get_object_or_404(Portal, owner__username=username)

    if not can_edit_portal(request.user, portal):
        raise PermissionDenied

    if request.method != 'POST':
        return render(request, 'portals/delete-portal.html')
    else:
        if 'confirmation' in request.POST:
            portal.root.delete()
            portal.delete()
            return redirect('/')
        else:
            return redirect(portal_url(username, action='manage_portal'))
