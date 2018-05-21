import six
from django import template
from django.template import Node, TemplateSyntaxError
from django.utils.module_loading import import_string

from oioioi.base.menu import MenuRegistry, menu_registry

register = template.Library()


class GenerateMenuNode(Node):
    def __init__(self, registry):
        self.registry = registry

    def render(self, context):
        request = context['request']
        registry = self.registry.resolve(context)
        if not registry:
            registry = menu_registry
        if isinstance(registry, six.string_types):
            registry = import_string(registry)
        if not isinstance(registry, MenuRegistry):
            raise TemplateSyntaxError("{%% generate_menu %%} got an "
                    "argument which is not a MenuRegistry: %r" % (registry,))
        context['menu'] = registry.template_context(request)
        return ''


@register.tag
def generate_menu(parser, token):
    """A template tag which produces the menu.

       Adds a ``menu`` key to the template context, which is a list of
       dictionaries, each represnting a single menu item. Each of them has two
       keys: ``name``, ``text`` and ``url``.

       Usage with default menu registry
       (:data:`oioioi.base.menu.menu_registry`):

       .. code-block:: html+django

           {% load menu %}

           {% generate_menu %}
           {% for item in menu %}
               <li>
               <a href="{{ item.url }}" {{ item.attrs }}>{{ item.text }}</a>
               </li>
           {% endfor %}

       Usage with non-default menu registry:

       .. code-block:: html+django

           {% load menu %}

           {% generate_menu 'oioioi.base.admin.admin_menu_registry' %}
           {% for item in menu %}
               <li>
               <a href="{{ item.url }}" {{ item.attrs }}>{{ item.text }}</a>
               </li>
           {% endfor %}

       It's also possible to pass a variable containing an instance of
       :class:`~oioioi.base.menu.MenuRegistry` as an argument.
    """
    bits = token.split_contents()
    if len(bits) > 2:
        raise TemplateSyntaxError("Unexpected arguments to {%% %s %%}" %
                (bits[0],))
    if len(bits) == 2:
        target = parser.compile_filter(bits[1])
        return GenerateMenuNode(target)
    else:
        return GenerateMenuNode('""')
