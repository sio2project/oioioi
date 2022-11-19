from django.template import Library
from oioioi.portals.utils import join_paths

register = Library()


@register.inclusion_tag('portals/breadcrumbs.html', takes_context=True)
def breadcrumbs(context):
    cur_node = context['current_node']
    ancestors = cur_node.get_ancestors(include_self=True)

    node_paths = []
    path = ''
    for node in ancestors:
        path = join_paths(path, node.short_name)
        node_paths.append((node, path))

    return {
        'node_paths': node_paths,
        'current_node': cur_node,
        'request': context['request'],
    }
