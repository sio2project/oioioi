from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404


def join_paths(path1, path2):
    if not path1:
        return path2
    elif not path2:
        return path1
    else:
        return path1 + '/' + path2


def parent_path(path):
    return '/'.join(path.split('/')[:-1])


def portal_url(username, path='', action='show'):
    url = reverse('portal', kwargs={'username': username,
                                    'portal_path': path})
    if action != 'show':
        url += '?action=' + action
    return url


def can_edit_portal(user, portal):
    return user.is_superuser or user == portal.owner


def get_node_context(request, username, portal_path):
    portal_path = portal_path.strip('/')
    path_list = portal_path.split('/') if portal_path else []

    try:
        owner = User.objects.get(username=username)
        portal = owner.portal
        node = portal.root
        for node_name in path_list:
            node = node.get_children().get(short_name=node_name)
    except ObjectDoesNotExist:
        raise Http404

    return {'current_node': node, 'owner': owner,
            'can_edit': can_edit_portal(request.user, portal)}


def get_edit_node_context(request, username, portal_path):
    context = get_node_context(request, username, portal_path)
    if not context['can_edit']:
        raise PermissionDenied
    return context
