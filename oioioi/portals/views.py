import json

from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from mptt.exceptions import InvalidMove
from collections import OrderedDict

from oioioi.base.main_page import register_main_page_view
from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import (enforce_condition, is_superuser,
                                     not_anonymous)
from oioioi.portals.actions import (DEFAULT_ACTION_NAME, node_actions,
                                    portal_actions, portal_url,
                                    register_node_action,
                                    register_portal_action)
from oioioi.portals.conditions import (current_node_is_root,
                                       main_page_from_default_global_portal,
                                       is_portal_admin)
from oioioi.portals.forms import NodeForm, PortalsSearchForm, PortalInfoForm, \
    PortalShortDescForm, LinkNameForm
from oioioi.portals.models import Node, Portal
from oioioi.portals.utils import resolve_path
from oioioi.portals.widgets import render_panel

# pylint: disable=W0611
import oioioi.portals.handlers


@register_main_page_view(order=500,
                         condition=main_page_from_default_global_portal)
def main_page_view(request):
    return redirect(reverse('global_portal', kwargs={'link_name': 'default',
                                                     'portal_path': ''}))


def redirect_old_global_portal(request, portal_path):
    """ View created for historical reasons - there used to be
    only one global portal allowed, with 'portal' as its path prefix
    hardcoded in url. Since it is possible to created more than one
    global portal, old unique global portal shall be changed to global
    portal with link_name='default' (see migrations). To keep old,
    saved users links viable they must be redirected to new address
    and here comes that function."""
    return redirect(reverse('global_portal',
                            kwargs={'link_name': 'default',
                                    'portal_path': portal_path}))


@enforce_condition(is_superuser, login_redirect=False)
def create_global_portal_view(request):

    if request.method == 'POST':
        form = LinkNameForm(request.POST)
        if 'confirmation' in request.POST:
            if form.is_valid():
                name = render_to_string(
                        'portals/global-portal-initial-main-page-name.txt')
                body = render_to_string(
                        'portals/global-portal-initial-main-page-body.txt')
                root = Node.objects.create(full_name=name, short_name='',
                                           parent=None, panel_code=body)
                portal = Portal(owner=None, root=root)
                form = LinkNameForm(request.POST, instance=portal)
                form.save()
                return redirect(portal_url(portal=portal))
        else:
            return redirect(reverse('portals_main_page_type',
                                    kwargs={'view_type': 'global'}))
    else:
        form = LinkNameForm()
    return render(request, 'portals/create-global-portal.html', {'form': form})


@enforce_condition(not_anonymous, login_redirect=False)
def create_user_portal_view(request):
    portal_queryset = Portal.objects.filter(owner=request.user)
    if portal_queryset.exists():
        return redirect(portal_url(portal=portal_queryset.get()))

    if request.method != 'POST':
        return render(request, 'portals/create-user-portal.html')
    else:
        if 'confirmation' in request.POST:
            name = render_to_string(
                    'portals/user-portal-initial-main-page-name.txt')
            body = render_to_string(
                    'portals/user-portal-initial-main-page-body.txt')
            root = Node.objects.create(full_name=name, short_name='',
                                       parent=None, panel_code=body)
            portal = Portal.objects.create(owner=request.user, root=root)
            return redirect(portal_url(portal=portal))
        else:
            return redirect(reverse('portals_main_page'))


def _portal_view(request, portal, portal_path):
    if 'action' in request.GET:
        action = request.GET['action']
    else:
        action = DEFAULT_ACTION_NAME

    request.portal = portal
    request.action = action

    if action in node_actions:
        request.current_node = resolve_path(request.portal, portal_path)
        view = node_actions[action]
    elif action in portal_actions:
        view = portal_actions[action]
    else:
        raise Http404

    return view(request)


def global_portal_view(request, link_name, portal_path):
    portal = get_object_or_404(Portal, link_name=link_name)
    return _portal_view(request, portal, portal_path)


def user_portal_view(request, username, portal_path):
    portal = get_object_or_404(Portal, owner__username=username)
    return _portal_view(request, portal, portal_path)


@register_node_action('show_node', menu_text=_("Show node"), menu_order=100)
def show_node_view(request):
    rendered_panel = mark_safe(render_panel(request,
                                            request.current_node.panel_code))
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
    if request.method == 'POST':
        if request.user.is_superuser:
            form = PortalInfoForm(request.POST, instance=request.portal)
        else:
            form = PortalShortDescForm(request.POST, instance=request.portal)
        if form.is_valid():
            portal = form.save(commit=False)
            portal.save()

    else:
        if request.user.is_superuser:
            form = PortalInfoForm(instance=request.portal)
        else:
            form = PortalShortDescForm(instance=request.portal)
    return render(request, 'portals/manage-portal.html', {'form': form})


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
            return redirect(reverse('portals_main_page'))
        else:
            return redirect(portal_url(portal=request.portal,
                                       action='manage_portal'))


def my_portal_url(request):
    try:
        return portal_url(portal=request.user.portal)
    except Portal.DoesNotExist:
        return reverse('create_user_portal')


@enforce_condition(not_anonymous, login_redirect=False)
def render_markdown_view(request):
    if request.method != 'POST' or 'markdown' not in request.POST:
        raise Http404
    rendered = render_panel(request, request.POST['markdown'])
    return HttpResponse(json.dumps({'rendered': rendered}),
                        content_type='application/json')


def portals_main_page_view(request, view_type='public'):

    if request.user.is_superuser:
        page_title = _('Portals main page')
        views = OrderedDict([('public', _('Public portals')),
                             ('all', _('All portals')),
                             ('global', _('Global portals'))])

        if request.method == 'GET':
            query = request.GET.get('q', '')
            form = PortalsSearchForm(query=query)
            if view_type == 'public':
                # search query in public portals
                portals_to_display = \
                    Portal.objects.filter(Q(is_public=True) &
                                          (Q(owner__username__icontains=query)
                                           | Q(root__full_name__icontains=query)
                                           | Q(link_name__icontains=query)))
            elif view_type == 'all':
                # search query in all portals
                portals_to_display = Portal.objects.filter(
                    Q(owner__username__icontains=query)
                    | Q(root__full_name__icontains=query)
                    | Q(link_name__icontains=query))
            elif view_type == 'global':
                # search query in global portals
                portals_to_display = \
                    Portal.objects.filter(Q(owner=None) &
                                          (Q(root__full_name__icontains=query)
                                           | Q(link_name__icontains=query)))
            else:
                raise Http404

        else:
            form = PortalsSearchForm()
            portals_to_display = Portal.objects.filter(is_public=True)

    else:
        page_title = _('Public portals')
        portals_to_display = Portal.objects.filter(is_public=True)
        form = None
        views = None
    return render(request, 'portals/portals_main_page.html',
                  {'portals': portals_to_display,
                   'page_title': page_title,
                   'form': form,
                   'views': views,
                   'curr_view_type': view_type})


account_menu_registry.register('my_portal', _("My portal"), my_portal_url,
        order=150)
