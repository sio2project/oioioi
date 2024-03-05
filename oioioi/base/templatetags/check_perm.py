from django import template
from django.template import Node, TemplateSyntaxError, Variable

register = template.Library()


class CheckPermNode(Node):
    def __init__(self, perm, obj, var):
        self.perm = Variable(perm)
        self.obj = Variable(obj)
        self.var = var

    def render(self, context):
        try:
            perm = self.perm.resolve(context)
            obj = self.obj.resolve(context)
        # pylint: disable=broad-except
        except Exception:
            context[self.var] = False
        else:
            user = context['user']
            context[self.var] = user.has_perm(perm, obj)
        return ''


@register.tag
def check_perm(parser, token):
    """A template tag to look up object permissions.

    The current user is tested agains the given permission on the given
    object. Current user is taken from the template context, so the
    ``django.contrib.auth.context_processors.auth`` template context
    processor must be present in ``settings.TEMPLATE_CONTEXT_PROCESSORS``.

    Usage:

    .. code-block:: html+django

        {% load check_perm %}

        {% check_perm "some_permission" for some_object as variable %}
        {% if variable %}
        <p>This is shown if the user has some_permission on some_object.</p>
        {% endif %}
    """
    bits = token.split_contents()
    format = '{% has_perm "some_permission" for some_object as variable %}'
    if len(bits) != 6 or bits[2] != 'for' or bits[4] != 'as':
        raise TemplateSyntaxError("check_perm tag should look like this: " + format)
    return CheckPermNode(bits[1], bits[3], bits[5])
