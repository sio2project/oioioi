"""The status app provides common ground for fetching updates from server.

   To get your data returned when asking for ``reverse('get_status')``,
   you have to register a function to :data:`oioioi.status.status_registry`.
   This function should act similar to programs handlers: take ``request``
   and dictionary ``response`` -- output of previous functions,
   alter ``response`` and return it.
"""
from oioioi.base.menu import OrderedRegistry


status_registry = OrderedRegistry()
