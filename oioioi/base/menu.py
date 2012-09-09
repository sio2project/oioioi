# coding: utf-8

from operator import attrgetter
import sys

_menu_items = []

class _MenuItem(object):
    def __init__(self, name, text, url_generator, order, condition):
        self.name = name
        self.text = text
        self.url_generator = url_generator
        self.order = order
        self.condition = condition

class MenuRegistry(object):
    """Maintains a collection of menu items."""

    def __init__(self):
        self.items = []

    def register(self, name, text, url_generator, order=sys.maxint,
            condition=None):
        """Registers a new menu item.

        :param name: a short identifier, for example used to find a matching
                        icon etc.
        :param text: text to display
        :param url_generator: generates menu link URL
        :type url_generator: fun: request → str
        :param order: value determining the order of items
        :type order: int
        :param condition: decides if the item should be shown
        :type condition: fun: request → bool

        Menu items should be registered in ``views.py`` of Django apps.
        """

        if condition is None:
            condition = lambda request: True

        menu_item = _MenuItem(name, text, url_generator, order, condition)
        self.items.append(menu_item)
        self.items.sort(key=attrgetter('order'))

    def unregister(self, name):
        """Unregisters a menu item.

        Does nothing if not found.
        """

        for index, item in enumerate(self.items):
            if item['name'] == name:
                break
        else:
            return
        del self.items[index]

    def template_context(self, request):
        """Returns a list of items to pass to a template for rendering."""
        context_items = []
        for item in self.items:
            try:
                if item.condition(request):
                    context_items.append(dict(
                        url=item.url_generator(request),
                        text=item.text))
            except Exception:
                pass
        return context_items

#: The default menu registry. Modules should use this to register menu items
#: commonly accessible to users.
menu_registry = MenuRegistry()

#: The menu registry for the user menu, shown as a drop down when a logged in
#: user clicks on its login in the navbar.
account_menu_registry = MenuRegistry()
