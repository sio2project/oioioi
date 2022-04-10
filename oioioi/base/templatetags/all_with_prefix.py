from django import template
from django.template import Node, TemplateSyntaxError
from django.utils.encoding import force_str

register = template.Library()


class AllWithPrefixNode(Node):
    def __init__(self, prefix):
        self.prefix = prefix

    def render(self, context):
        flattened_context = {}
        for d in context.dicts:
            flattened_context.update(d)
        to_render = [
            value
            for key, value in flattened_context.items()
            if key.startswith(self.prefix)
        ]
        return ''.join(map(force_str, to_render))


@register.tag
def all_with_prefix(parser, token):
    """Concatenates all values from the context which start with the
    prefix given as the only parameter."""
    try:
        _tag_name, prefix = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise TemplateSyntaxError(msg)
    return AllWithPrefixNode(prefix)
