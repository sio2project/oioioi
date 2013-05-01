# coding: utf-8
import bisect
import sys

from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape
from django.utils.safestring import mark_safe


class OrderedRegistry(object):
    """Maintains a collection of values ordered by a separate key."""

    def __init__(self):
        self.items = []
        self.keys = []

    def register(self, value, order=sys.maxint):
        pos = bisect.bisect_right(self.keys, order)
        self.items.insert(pos, value)
        self.keys.insert(pos, order)
        return value

    def unregister(self, value):
        pos = self.items.index(value)
        del self.items[pos]
        del self.keys[pos]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)


class _MenuItem(object):
    def __init__(self, name, text, url_generator, condition, attrs):
        self.name = name
        self.text = text
        self.url_generator = url_generator
        self.condition = condition
        self.attrs = attrs


class MenuRegistry(object):
    """Maintains a collection of menu items.

       :param text: menu name to display (if appropriate)
       :param condition: decides if menu should be considered as available
       :type condition: :class:`oioioi.base.permissions.Condition`
    """

    def __init__(self, text=None, condition=None):
        self.text = text
        if condition is None:
            condition = lambda request: True
        self.condition = condition
        self._registry = OrderedRegistry()

    def register(self, name, text, url_generator, order=sys.maxint,
            condition=None, attrs=None):
        """Registers a new menu item.

           :param name: a short identifier, for example used to find a matching
                           icon etc.
           :param text: text to display
           :param url_generator: generates menu link URL
           :type url_generator: fun: request → str
           :param order: value determining the order of items
           :type order: int
           :param condition: decides if the item should be shown
           :type condition: :class:`oioioi.base.permissions.Condition`

           Menu items should be registered in ``views.py`` of Django apps.
        """

        if condition is None:
            condition = lambda request: True

        if attrs is None:
            attrs = {}

        menu_item = _MenuItem(name, text, url_generator, condition, attrs)
        self._registry.register(menu_item, order)

    def register_decorator(self, text, url_generator,
                           order=sys.maxint, attrs=None):
        """Decorator for a view which registers a new menu item. It accepts the
           same arguments as the :meth:`MenuRegistry.register`, except for
           ``name``, which is inferred from the view function name ('_view'
           suffix is stripped) and ``condition`` which is taken from the view
           attribute of the same name (assigned for example by
           :func:`oioioi.base.permissions.enforce_condition`).
        """
        def decorator(view_func):
            name = view_func.__name__
            suffix_to_remove = '_view'
            if name.endswith(suffix_to_remove):
                name = name[:-len(suffix_to_remove)]
            if hasattr(view_func, 'condition'):
                condition = view_func.condition
            else:
                condition = lambda request: True
            self.register(name, text, url_generator, order, condition, attrs)
            return view_func
        return decorator

    def unregister(self, name):
        """Unregisters a menu item.

           Does nothing if not found.
        """

        for item in self._registry:
            if item.name == name:
                self._registry.unregister(item)
                break

    def template_context(self, request):
        """Returns a list of items to pass to a template for rendering."""
        if not self.condition(request):
            return []

        context_items = []
        for item in self._registry:
            if item.condition(request):
                attrs_str = ' '.join(['%s="%s"' % (escape(k), escape(v))
                    for (k, v) in item.attrs.items()])
                attrs_str = mark_safe(attrs_str)
                context_items.append(dict(
                    url=item.url_generator(request),
                    text=item.text,
                    attrs=attrs_str))
        return context_items

#: The default menu registry. Modules should use this to register menu items
#: commonly accessible to users.
menu_registry = MenuRegistry(_("User Menu"))

#: The menu registry for the user menu, shown as a drop down when a logged in
#: user clicks on its login in the navbar.
account_menu_registry = MenuRegistry(_("Account Menu"),
        lambda request: request.user.is_authenticated())

#: The registry for *menus* displayed on the side.
side_pane_menus_registry = OrderedRegistry()
side_pane_menus_registry.register(menu_registry, order=1000)
