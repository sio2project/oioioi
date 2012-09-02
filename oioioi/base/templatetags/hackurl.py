from django import template
from django.template import defaulttags, Node

register = template.Library()

class ExceptionHandlingNode(Node):
    def __init__(self, wrapped_node, error_message):
        self.wrapped_node = wrapped_node
        self.error_message = error_message

    def render(self, context):
        try:
            return self.wrapped_node.render(context)
        except Exception:
            return self.error_message

@register.tag
def hackurl(parser, token):
    # XXX: This is a temporary hack --- we defile a {% hackurl %} tag which
    #      does not throw exceptions if the url cannot be reversed.
    url_node = defaulttags.url(parser, token)
    return ExceptionHandlingNode(url_node, '#')

