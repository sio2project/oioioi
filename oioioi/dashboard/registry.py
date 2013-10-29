from oioioi.base.menu import OrderedRegistry

#: A registry containing fragments of the dashboard. Each fragment is a
#: callable which expects a single parameter --- the request --- and returns an
#: HTML string to render on the dashboard. It should return ``None`` if there
#: is no content to display.
dashboard_registry = OrderedRegistry()

#: A registry containing headers of the dashboard. They are just like regular
#: fragments above, except that a placeholder text "this is dashboard,
#: something will be shown here once you submit..." is shown only when there is
#: nothing rendered by functions registered in ``dashboard_registry``, even if
#: some headers are present.
dashboard_headers_registry = OrderedRegistry()
