import sys

from django.core.exceptions import ImproperlyConfigured

from oioioi.base.menu import OrderedRegistry
from oioioi.base.permissions import Condition


class _ContestDashboardEntry:
    def __init__(self, view, condition):
        self.view = view
        self.condition = condition


_contest_dashboard_registry = OrderedRegistry()


def register_contest_dashboard_view(order=sys.maxsize, condition=None):
    """Decorator for a view, which registers it as a contest dashboard.

    A view registered this way can be shown as the main page of the contest.
    If multiple views are registered, one with the lowest ``order`` for
    which the ``condition`` holds true is selected.

    :param order: value determining the order in which the dashboard is
                  selected
    :type order: int
    :param condition: decides if a dashboard can be selected
    :type condition: :class:`oioioi.base.permissions.Condition`
    """

    if condition is None:
        condition = Condition(lambda request: True)

    def decorator(view):
        _contest_dashboard_registry.register(_ContestDashboardEntry(view, condition), order)
        return view

    return decorator


def unregister_contest_dashboard_view(view):
    """Unregisters a contest dashboard view.

    Does nothing if not found.

    :param view: the dashboard view to unregister
    """

    for entry in _contest_dashboard_registry:
        if entry.view is view:
            _contest_dashboard_registry.unregister(entry)
            return


def contest_dashboard_view(request):
    for entry in _contest_dashboard_registry:
        if entry.condition(request):
            return entry.view(request)

    raise ImproperlyConfigured("No contest dashboard has been registered")
