# coding: utf-8
import bisect
import sys
from operator import attrgetter  # pylint: disable=E0611

from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.base.permissions import Condition

class OrderedRegistry(object):
    """Maintains a collection of values ordered by a separate key."""

    def __init__(self):
        self.items = []
        self.keys = []

    def register(self, value, order=sys.maxsize):
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

    def register_decorator(self, order=sys.maxsize):
        def decorator(func):
            self.register(func, order)
            return func

        return decorator


class MenuItem(object):
    """Used to store single menu entry.

    :param name: a short identifier, for example used to find a matching
                    icon etc.
    :param text: text to display
    :param url_generator: generates menu link URL
    :type url_generator: fun: request → str
    :param order: value determining the order of items in menu
    :type order: int
    :param condition: decides if the item should be shown
    :type condition: :class:`oioioi.base.permissions.Condition`
    """

    def __init__(
        self, name, text, url_generator, condition=None, attrs=None, order=sys.maxsize
    ):

        if condition is None:
            condition = Condition(lambda request: True)

        if attrs is None:
            attrs = {}

        if order is None:
            order = sys.maxsize

        self.name = name
        self.text = text
        self.url_generator = url_generator
        self.condition = condition
        self.attrs = attrs
        self.order = order


class MenuRegistry(object):
    """Maintains a collection of menu items.

    :param text: menu name to display (if appropriate)
    :param condition: decides if menu should be considered as available
    :type condition: :class:`oioioi.base.permissions.Condition`
    """

    def _get_all_registered_items(self, request):
        items = []
        for generator in self._generators.values():
            items.extend(generator(request))
        items.extend(self._registry)

        return items

    def __init__(self, text=None, condition=None, show_icons=False):
        self.text = text
        if condition is None:
            condition = lambda request: True
        self.condition = condition
        self.show_icons = show_icons
        self._registry = []
        self._generators = {}

    def register(
        self, name, text, url_generator, condition=None, attrs=None, order=sys.maxsize
    ):
        """Registers a new menu item.

        Menu items should be registered in ``views.py`` of Django apps.
        """

        menu_item = MenuItem(name, text, url_generator, condition, attrs, order)
        self._registry.append(menu_item)

    def register_decorator(
        self, text, url_generator, condition=None, attrs=None, order=sys.maxsize
    ):
        """Decorator for a view which registers a new menu item. It accepts the
        same arguments as the :meth:`MenuRegistry.register`, except for
        ``name``, which is inferred from the view function name ('_view'
        suffix is stripped). ``condition`` is combined with the condition
        taken from the view attribute of the same name (assigned for example
        by :func:`oioioi.base.permissions.enforce_condition`).
        ``condition`` parameter influences only on visibility of menu entry
        but not on permission to see the page.
        """

        def decorator(view_func):
            name = view_func.__name__
            suffix_to_remove = '_view'
            if name.endswith(suffix_to_remove):
                name = name[: -len(suffix_to_remove)]
            if hasattr(view_func, 'condition'):
                current_condition = view_func.condition
            else:
                current_condition = Condition(lambda request: True)
            if condition is not None:
                current_condition = current_condition & condition
            self.register(name, text, url_generator, current_condition, attrs, order)
            return view_func

        return decorator

    def register_generator(self, name, items_generator):
        """Registers a new menu items generator.

        :param name: a short identifier
        :param items_generator: generates list of menu items
        :type items_generator: fun: request → [MenuItem]
        """
        assert name not in self._generators
        self._generators[name] = items_generator

    def unregister(self, name):
        """Unregisters a menu item.

        Does nothing if not found.
        """

        for item in self._registry:
            if item.name == name:
                pos = self._registry.index(item)
                del self._registry[pos]
                break

    def unregister_generator(self, name):
        """Unregisters a menu items generator.

        Does nothing if not found.
        """

        if name in self._generators:
            del self._generators[name]

    def template_context(self, request):
        """Returns a list of items to pass to a template for rendering."""
        if not self.condition(request):
            return []

        items = self._get_all_registered_items(request)

        context_items = []
        for item in sorted(items, key=attrgetter('order')):
            if item.condition(request):
                attrs_str = ' '.join(
                    [
                        '%s="%s"' % (escape(k), escape(v))
                        for (k, v) in item.attrs.items()
                    ]
                )
                attrs_str = mark_safe(attrs_str)
                context_items.append(
                    dict(
                        url=item.url_generator(request),
                        text=item.text,
                        attrs=attrs_str,
                        has_icon=self.show_icons,
                    )
                )
        return context_items

    def is_anything_accessible(self, request):
        """Returns whether any registered MenuItem is accessible in the given request"""
        if not self.condition(request):
            return False

        items = self._get_all_registered_items(request)
        for item in items:
            if item.condition(request):
                return True

        return False


#: The default menu registry. Modules should use this to register menu items
#: commonly accessible to users.
menu_registry = MenuRegistry(_("User Menu"), show_icons=True)

#: The menu registry for the user menu, shown as a drop down when a logged in
#: user clicks on its login in the navbar.
account_menu_registry = MenuRegistry(
    _("Account Menu"), lambda request: request.user.is_authenticated
)

#: The registry for *menus* displayed on the side.
side_pane_menus_registry = OrderedRegistry()
side_pane_menus_registry.register(menu_registry, order=1000)

personal_menu_registry = MenuRegistry(_("Personal Menu"))
side_pane_menus_registry.register(personal_menu_registry, order=50)

#: The registry for uncollapsed menu in the upper navigation bar.
navbar_links_registry = MenuRegistry(_("Navigation Bar Menu"))

