import sys

from django.core.urlresolvers import reverse

from oioioi.base.menu import MenuRegistry
from oioioi.base.permissions import Condition, enforce_condition
from oioioi.portals.conditions import is_portal_admin

portal_actions = {}
node_actions = {}
DEFAULT_ACTION_NAME = 'show_node'
portal_admin_menu_registry = MenuRegistry(condition=is_portal_admin)


def _register_portal_action(actions, name, condition, menu_text,
                            menu_url_generator, menu_order):
    if condition is None:
        condition = Condition(lambda request: True)

    def decorator(view):
        view = enforce_condition(condition, login_redirect=False)(view)
        actions[name] = view

        if menu_text is not None:
            portal_admin_menu_registry.register(name, menu_text,
                    menu_url_generator, condition, order=menu_order)

        return view

    return decorator


def register_portal_action(name, condition=None, menu_text=None,
                           menu_order=sys.maxsize):
    """Decorator for a view, which registers it as a portal action.

       A portal action is a view which operates on a portal. After
       registration, it is accessible at URL
       /users/username/portal/?action=``name``. You can specify a ``condition``
       under which the action can be accessed. The action can also be added to
       the portal admin menu. In order to do that, you have to specify
       ``menu_text``. If ``condition`` is specified, the action will not be
       visible in the admin buttons unless it is satisfied.

       For portal actions, the following ``request`` attributes are set:
       - ``portal`` - :class:`oioioi.portals.models.Portal` for which the
                      action is called, also set in the template context
       - ``action`` - action name

       :param name: action name, shown in the URL
       :param condition: decides if the action is accessible
       :type condition: :class:`oioioi.base.permissions.Condition`
       :param menu_text: text to display in the portal admin menu
       :param menu_order: value determining the order of items in the portal
                          admin menu
    """

    return _register_portal_action(portal_actions, name, condition, menu_text,
            lambda request: portal_url(portal=request.portal, action=name),
            menu_order)


def register_node_action(name, condition=None, menu_text=None,
                         menu_order=sys.maxsize):
    """Decorator for a view, which registers it as a node action.

       A node action is a view which operates on a portal node. After
       registration, it is accessible at URL
       /users/username/portal/path/to/node?action=``name``.

       For node actions, the following ``request`` attributes are set:
       - ``portal`` - :class:`oioioi.portals.models.Portal` for which the
                      action is called, also set in the template context
       - ``current_node`` - :class:`oioioi.portals.models.Node` for which the
                            action is called, also set in the template context
       - ``action`` - action name

       Parameters are the same as for
       :func:`oioioi.portals.actions.register_portal_action`.
    """
    return _register_portal_action(node_actions, name, condition, menu_text,
            lambda request: portal_url(node=request.current_node, action=name),
            menu_order)


def portal_url(portal=None, node=None, path=None, action=DEFAULT_ACTION_NAME):
    """Generates a portal action URL.

       This is an analog of :func:`django.core.urlresolvers.reverse` for portal
       actions. Three parameter sets are possible:
       - ``portal`` - generates URL to a portal action for ``portal`` or to
                      a node action for ``portal`` root
       - ``node`` - generates URL to a node action for ``node``
       - ``portal`` and ``path`` - generates URL to a node action for a node at
                                   ``path`` in ``portal``
       Specifying the parameters as named arguments is advised in order to
       avoid confusion.

       Also available as a template tag.

       :param portal: portal for which URL is generated
       :type portal: :class:`oioioi.portals.models.Portal`
       :param node: portal node for which URL is generated
       :type node: :class:`oioioi.portals.models.Node`
       :param path: path to the node for which URL is generated
       :param action: name of the action to which URL is generated
    """

    if portal is None:
        if node is None:
            raise TypeError('Either portal or node must be specified')
        portal = node.get_root().portal

    if path is None:
        if node is None:
            node = portal.root
        path = node.get_path()

    if portal.owner is None:
        url = reverse('global_portal', kwargs={'link_name': portal.link_name,
                                               'portal_path': path})
    else:
        url = reverse('user_portal', kwargs={'username': portal.owner.username,
                                             'portal_path': path})

    if action != DEFAULT_ACTION_NAME:
        url += '?action=' + action
    return url
