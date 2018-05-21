import sys

from django.core.exceptions import ImproperlyConfigured

from oioioi.base.menu import OrderedRegistry
from oioioi.base.permissions import Condition


class _MainPageEntry(object):
    def __init__(self, view, condition):
        self.view = view
        self.condition = condition


_main_page_registry = OrderedRegistry()


def register_main_page_view(order=sys.maxsize, condition=None):
    """Decorator for a view, which registers it as a main page.

       A view registered this way can be shown as the main page of the website
       (at URL /). If multiple views are registered, one with the lowest
       ``order`` for which the ``condition`` holds true is selected.

       :param order: value determining the order in which the main page is
                     selected
       :type order: int
       :param condition: decides if a main page can be selected
       :type condition: :class:`oioioi.base.permissions.Condition`
    """

    if condition is None:
        condition = Condition(lambda request: True)

    def decorator(view):
        _main_page_registry.register(_MainPageEntry(view, condition), order)
        return view

    return decorator


def unregister_main_page_view(view):
    """Unregisters a main page view.

       Does nothing if not found.

       :param view: the main page view to unregister
    """

    for entry in _main_page_registry:
        if entry.view is view:
            _main_page_registry.unregister(entry)
            return


def main_page_view(request):
    for entry in _main_page_registry:
        if entry.condition(request):
            return entry.view(request)

    raise ImproperlyConfigured("No main page has been registered")
