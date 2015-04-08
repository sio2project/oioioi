from oioioi.base.menu import OrderedRegistry


profile_registry = OrderedRegistry()


def profile_section(order):
    """ Decorator for registering profile view sections.

        The decorated function is passed the request and shown user.
    """
    return profile_registry.register_decorator(order)
