import json

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import get_language_from_request
from django.utils.translation import gettext_lazy as _
from mptt.exceptions import InvalidMove

# pylint: disable=W0611
import oioioi.portals.handlers
from oioioi.base.main_page import register_main_page_view
from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition, is_superuser, not_anonymous
from oioioi.portals.actions import (
    DEFAULT_ACTION_NAME,
    node_actions,
    portal_actions,
    portal_url,
    register_node_action,
    register_portal_action,
)
from oioioi.portals.conditions import (
    current_node_is_root,
    is_portal_admin,
    main_page_from_default_global_portal,
)
from oioioi.portals.forms import (
    LinkNameForm,
    NodeForm,
    NodeLanguageVersionFormset,
    PortalInfoForm,
    PortalShortDescForm,
    PortalsSearchForm,
)
from oioioi.portals.models import Node, NodeLanguageVersion, Portal
from oioioi.portals.utils import resolve_path
from oioioi.portals.widgets import render_panel
from oioioi.portals.handlers import update_task_information_cache

from oioioi.problems.problem_site import problem_site_tab


@register_main_page_view(order=500, condition=main_page_from_default_global_portal)
def main_page_view(request):
    return redirect(
        reverse('global_portal', kwargs={'link_name': 'default', 'portal_path': ''})
    )


def redirect_old_global_portal(request, portal_path):
    """View created for historical reasons - there used to be
    only one global portal allowed, with 'portal' as its path prefix
    hardcoded in url. Since it is possible to create more than one
    global portal, old unique global portal shall be changed to global
    portal with link_name='default' (see migrations). To keep old,
    saved users links viable they must be redirected to new address
    and here comes that function."""
    return redirect(
        reverse(
            'global_portal', kwargs={'link_name': 'default', 'portal_path': portal_path}
        )
    )


def create_root_node(lang):
    """Creates a root node with the given language.
    The new node contains default title and body.
    """
    name = render_to_string('portals/portal-initial-main-page-name.txt')
    body = render_to_string('portals/portal-initial-main-page-body.txt')
    root = Node.objects.create(short_name='', parent=None)
    NodeLanguageVersion.objects.create(
        language=lang, full_name=name, panel_code=body, node=root
    )
    return root


@enforce_condition(is_superuser, login_redirect=False)
def create_global_portal_view(request):
    if request.method == 'POST':
        form = LinkNameForm(request.POST)
        if 'confirmation' in request.POST:
            if form.is_valid():
                lang = get_language_from_request(request)
                root = create_root_node(lang)
                portal = Portal(owner=None, root=root)
                form = LinkNameForm(request.POST, instance=portal)
                form.save()
                return redirect(portal_url(portal=portal))
        else:
            return redirect(
                reverse('portals_main_page_type', kwargs={'view_type': 'global'})
            )
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
            lang = get_language_from_request(request)
            root = create_root_node(lang)
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
    request.is_portal_admin = is_portal_admin(request)

    if action in node_actions:
        request.current_node = resolve_path(request.portal, portal_path)
        request.current_lang_version = request.current_node.get_lang_version(request)
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


@register_node_action('show_node', menu_text=_("View page"), menu_order=100)
def show_node_view(request):
    rendered_panel = mark_safe(
        render_panel(request, request.current_node.get_lang_version(request).panel_code)
    )
    return render(request, 'portals/show-node.html', {'rendered_panel': rendered_panel})


@register_node_action(
    'edit_node', condition=is_portal_admin, menu_text=_("Edit page"), menu_order=200
)
def edit_node_view(request):
    if request.method != 'POST':
        current_language = get_language_from_request(request)
        languages = [lang_short for lang_short, _ in settings.LANGUAGES]
        queryset = NodeLanguageVersion.objects.filter(node=request.current_node)

        for node_language_version in queryset:
            languages.remove(node_language_version.language)

        formset = NodeLanguageVersionFormset(
            initial=[
                {'language': lang, 'DELETE': lang != current_language}
                for lang in languages
            ],
            instance=request.current_node,
        )

        form = NodeForm(instance=request.current_node)
    else:
        form = NodeForm(request.POST, instance=request.current_node)
        formset = NodeLanguageVersionFormset(request.POST)

        if form.is_valid():
            node = form.save(commit=False)
            formset = NodeLanguageVersionFormset(request.POST, instance=node)

            if formset.is_valid():
                node.save()
                formset.save()
                update_task_information_cache(node)
                return redirect(portal_url(node=node))

    return render(
        request,
        'portals/edit-node.html',
        {
            'form': form,
            'formset': formset,
        },
    )


@register_node_action(
    'add_node', condition=is_portal_admin, menu_text=_("Add a subpage"), menu_order=300
)
def add_node_view(request):
    if request.method != 'POST':
        form = NodeForm(initial={'parent': request.current_node})
        current_language = get_language_from_request(request)
        formset = NodeLanguageVersionFormset(
            initial=[
                {'language': lang_short, 'DELETE': lang_short != current_language}
                for lang_short, lang_name in settings.LANGUAGES
            ],
            queryset=NodeLanguageVersion.objects.none(),
        )
    else:
        instance = Node(parent=request.current_node)
        form = NodeForm(request.POST, instance=instance)
        formset = NodeLanguageVersionFormset(request.POST)

        if form.is_valid():
            node = form.save(commit=False)
            formset = NodeLanguageVersionFormset(request.POST, instance=node)

            if formset.is_valid():
                node.save()
                formset.save()
                update_task_information_cache(node)
                return redirect(portal_url(node=node))

    return render(
        request,
        'portals/add-node.html',
        {
            'form': form,
            'formset': formset,
        },
    )


@register_node_action(
    'delete_node',
    condition=is_portal_admin & ~current_node_is_root,
    menu_text=_("Delete page"),
    menu_order=400,
)
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


@register_portal_action(
    'manage_portal',
    condition=is_portal_admin,
    menu_text=_("Manage portal"),
    menu_order=500,
)
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
    json_tree = render_to_string(
        'portals/portal-tree.json', {'nodes': nodes}, request=request
    )
    json_tree = json_tree.replace('}{', '},{')
    return HttpResponse(json_tree)


def move_node_view(request):
    position_mapping = {'before': 'left', 'after': 'right', 'inside': 'first-child'}
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
            return redirect(reverse('portals_main_page'))
        else:
            return redirect(portal_url(portal=request.portal, action='manage_portal'))


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
    return HttpResponse(
        json.dumps({'rendered': rendered}), content_type='application/json'
    )


def portals_main_page_view(request, view_type='public'):
    if request.user.is_superuser:
        page_title = _("Portals main page")
        views = [
            ('public', _("Public portals")),
            ('all', _("All portals")),
            ('global', _("Global portals")),
        ]

        if request.method == 'GET':
            query = request.GET.get('q', '')
            form = PortalsSearchForm(query=query)

            portal_search_q_expr = (
                Q(owner__username__icontains=query)
                | Q(root__language_versions__full_name__icontains=query)
                | Q(link_name__icontains=query)
            )
            if view_type == 'public':
                portal_search_q_expr &= Q(is_public=True)
            elif view_type == 'all':
                pass
            elif view_type == 'global':
                portal_search_q_expr &= Q(owner=None)
            else:
                raise Http404
            portals_to_display = Portal.objects.filter(portal_search_q_expr).distinct()
        else:
            form = PortalsSearchForm()
            portals_to_display = Portal.objects.filter(is_public=True)

    else:
        page_title = _("Public portals")
        portals_to_display = Portal.objects.filter(is_public=True)
        form = None
        views = None
    return render(
        request,
        'portals/portals_main_page.html',
        {
            'portals': portals_to_display.order_by('id'),
            'page_title': page_title,
            'form': form,
            'views': views,
            'curr_view_type': view_type,
        },
    )


@problem_site_tab(
    _("Related portal pages"),
    key='related_portal_pages',
    order=1000,
)
def problem_site_related_portal_pages(request, problem):
    pages = problem.portal_pages.all()
    pages = [
        (page.get_lang_version(request), page.get_root().portal)
        for page in pages
        if page.get_root().portal.is_public
    ]
    return TemplateResponse(
        request,
        'portals/related-portal-pages.html',
        {'pages': pages},
    )


account_menu_registry.register('my_portal', _("My portal"), my_portal_url, order=150)
