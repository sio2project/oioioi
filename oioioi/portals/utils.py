from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from oioioi.base.permissions import make_request_condition


def join_paths(path1, path2):
    if not path1:
        return path2
    elif not path2:
        return path1
    else:
        return path1 + '/' + path2


def parent_path(path):
    return '/'.join(path.split('/')[:-1])


def resolve_path(portal, path):
    path = path.strip('/')
    path = path.split('/') if path else []

    try:
        node = portal.root
        for node_name in path:
            node = node.get_children().get(short_name=node_name)
    except ObjectDoesNotExist:
        raise Http404

    return node
